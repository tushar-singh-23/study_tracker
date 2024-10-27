from flask import Blueprint, render_template, request, redirect, url_for, jsonify
from app import db
from app.models import Lesson, StudyDate, UserSettings
from app.utils import load_lessons_from_csv, calculate_progress, calculate_next_review_date, get_daily_schedule, calculate_study_plan
from app.forms import UpdateLessonForm, UserSettingsForm
from datetime import datetime
from sqlalchemy.sql import func

bp = Blueprint('main', __name__)

@bp.route('/')
def index():
    lessons_from_csv = load_lessons_from_csv()
    progress = calculate_progress()
    return render_template('index.html', progress=progress, datetime=datetime)

@bp.route('/add_lesson', methods=['GET', 'POST'])
def add_lesson():
    if request.method == 'POST':
        topic = request.form['topic']
        lesson_name = request.form['lesson_name']
        confidence_level = int(request.form['confidence_level'])
        last_studied = datetime.strptime(request.form['last_studied'], '%Y-%m-%d').date()
        next_review_date, interval, ease_factor = calculate_next_review_date(
            confidence_level, last_studied)

        new_lesson = Lesson(
            topic=topic,
            lesson_name=lesson_name,
            confidence_level=confidence_level,
            last_studied=last_studied,
            next_review_date=next_review_date,
            interval=interval,
            ease_factor=ease_factor
        )
        db.session.add(new_lesson)
        db.session.commit()
        return redirect(url_for('index'))
    return render_template('lessons/add.html')

@bp.route('/update_lesson/<lesson_id>', methods=['GET', 'POST'])
def update_lesson(lesson_id):
    """Update a specific lesson's confidence level, study time, and notes."""
    form = UpdateLessonForm()
    db_lesson = Lesson.query.filter_by(lesson_id=lesson_id).first_or_404()
    lesson_details = next((l for l in load_lessons_from_csv() if l['lesson_id'] == lesson_id), None)
    if form.validate_on_submit():
        confidence_level = form.confidence_level.data
        study_time = form.study_time.data
        notes = form.notes.data
        last_studied = datetime.utcnow().date()
        next_review_date, interval, ease_factor = calculate_next_review_date(
            confidence_level, last_studied, db_lesson.interval, db_lesson.ease_factor)
        
        # Update Lesson
        db_lesson.confidence_level = confidence_level
        db_lesson.last_studied = last_studied
        db_lesson.next_review_date = next_review_date
        db_lesson.interval = interval
        db_lesson.ease_factor = ease_factor
        
        # Record Study Session
        study_date = StudyDate(
            lesson_id=lesson_id,
            date=last_studied,
            study_time=study_time,
            notes=notes
        )
        db.session.add(study_date)
        db.session.commit()
        return redirect(url_for('main.view_topic', topic_name=lesson_details['topic']))
    elif request.method == 'GET':
        form.confidence_level.data = db_lesson.confidence_level
        form.study_time.data = 60  # Default value
        form.notes.data = ''
    return render_template('lessons/update.html', form=form, lesson_details=lesson_details, datetime=datetime)

@bp.route('/set_new_lesson', methods=['POST'])
def set_new_lesson():
    lesson_id = request.form.get('lesson_id')
    db_lesson = Lesson.query.filter_by(lesson_id=lesson_id).first()
    if db_lesson:
        # Add the lesson to today's new lessons
        pass  # Implement logic as needed
    return redirect(url_for('schedule'))

@bp.route('/view_study_dates/<lesson_id>')
def view_study_dates(lesson_id):
    lesson = Lesson.query.filter_by(lesson_id=lesson_id).first_or_404()
    study_dates = StudyDate.query.filter_by(lesson_id=lesson_id).order_by(StudyDate.date.desc()).all()
    lesson_details = next((l for l in load_lessons_from_csv() if l['lesson_id'] == lesson_id), None)
    return render_template('lessons/view.html', lesson=lesson, study_dates=study_dates, lesson_details=lesson_details)

@bp.route('/schedule', methods=['GET', 'POST'])
def schedule():
    """Display and manage today's study schedule."""
    today = datetime.utcnow().date()
    lessons_from_csv = load_lessons_from_csv()
    revisions, new_lessons = get_daily_schedule(today)
    available_new_lessons = [lesson for lesson in lessons_from_csv if Lesson.query.filter_by(lesson_id=lesson['lesson_id'], confidence_level=0).first()]
    study_plan = calculate_study_plan(today)
    if request.method == 'POST':
        selected_lesson_id = request.form.get('selected_lesson')
        db_lesson = Lesson.query.filter_by(lesson_id=selected_lesson_id).first()
        if db_lesson:
            # Schedule the selected lesson for today
            db_lesson.scheduled_for_today = True
            db.session.commit()
            return redirect(url_for('schedule'))
    return render_template('schedule/schedule.html', revisions=revisions, new_lessons=new_lessons, available_new_lessons=available_new_lessons, study_plan=study_plan, datetime=datetime)

@bp.route('/topic/<topic_name>')
def view_topic(topic_name):
    """Display all lessons within a specific topic."""
    lessons_from_csv = load_lessons_from_csv()
    topic_lessons = []
    for lesson in lessons_from_csv:
        if lesson['topic'] == topic_name:
            db_lesson = Lesson.query.filter_by(lesson_id=lesson['lesson_id']).first()
            if db_lesson:
                # Calculate average study time
                avg_study_time = db.session.query(func.avg(StudyDate.study_time)).filter_by(lesson_id=db_lesson.lesson_id).scalar()
                avg_study_time = round(avg_study_time) if avg_study_time else 60  # Default to 60 minutes
                lesson_data = {
                    'lesson_id': db_lesson.lesson_id,
                    'lesson_name': lesson['lesson_name'],
                    'confidence_level': db_lesson.confidence_level,
                    'next_review_date': db_lesson.next_review_date,
                    'last_studied': db_lesson.last_studied,
                    'notes': db_lesson.notes,
                    'avg_study_time': avg_study_time
                }
                topic_lessons.append(lesson_data)
    return render_template('lessons/topic_lessons.html', topic_name=topic_name, lessons=topic_lessons, datetime=datetime)

@bp.route('/settings', methods=['GET', 'POST'])
def settings():
    """Allow user to adjust their study time and completion date."""
    settings = UserSettings.query.first()
    form = UserSettingsForm(obj=settings)
    if form.validate_on_submit():
        settings.total_study_time_weekday = form.total_study_time_weekday.data
        settings.total_study_time_weekend = form.total_study_time_weekend.data
        settings.completion_date = form.completion_date.data
        db.session.commit()
        return redirect(url_for('main.index'))
    return render_template('settings.html', form=form, datetime=datetime)

@bp.route('/update_lesson_inline', methods=['POST'])
def update_lesson_inline():
    """Handle inline lesson updates via AJAX."""
    data = request.get_json()
    lesson_id = data.get('lesson_id')
    confidence_level = int(data.get('confidence_level'))
    last_studied = datetime.strptime(data.get('last_studied'), '%Y-%m-%d').date() if data.get('last_studied') else None
    notes = data.get('notes')
    
    db_lesson = Lesson.query.filter_by(lesson_id=lesson_id).first()
    if db_lesson:
        db_lesson.confidence_level = confidence_level
        db_lesson.last_studied = last_studied
        db_lesson.notes = notes
        db.session.commit()
        return jsonify({'success': True})
    else:
        return jsonify({'success': False}), 400

@bp.route('/study_history/<lesson_id>')
def study_history(lesson_id):
    """Display the study history for a specific lesson."""
    lesson = Lesson.query.filter_by(lesson_id=lesson_id).first_or_404()
    study_dates = StudyDate.query.filter_by(lesson_id=lesson_id).order_by(StudyDate.date.desc()).all()
    lesson_details = next((l for l in load_lessons_from_csv() if l['lesson_id'] == lesson_id), None)
    return render_template('lessons/study_history.html', lesson=lesson, lesson_details=lesson_details, study_dates=study_dates)
