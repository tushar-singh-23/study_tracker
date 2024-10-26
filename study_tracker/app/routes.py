from flask import Blueprint, render_template, request, redirect, url_for
from app import db
from app.models import Lesson, StudyDate
from app.utils import load_lessons_from_csv, calculate_progress, calculate_next_review_date, get_daily_schedule
from app.forms import UpdateLessonForm
from datetime import datetime

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
    form = UpdateLessonForm()
    db_lesson = Lesson.query.filter_by(lesson_id=lesson_id).first_or_404()
    lesson_details = next((l for l in load_lessons_from_csv() if l['lesson_id'] == lesson_id), None)
    if form.validate_on_submit():
        confidence_level = int(request.form['confidence_level'])
        notes = request.form.get('notes')
        last_studied = datetime.utcnow().date()
        next_review_date, interval, ease_factor = calculate_next_review_date(
            confidence_level, last_studied, db_lesson.interval, db_lesson.ease_factor)

        db_lesson.confidence_level = confidence_level
        db_lesson.last_studied = last_studied
        db_lesson.next_review_date = next_review_date
        db_lesson.interval = interval
        db_lesson.ease_factor = ease_factor
        db_lesson.notes = notes

        # Record the study date
        study_date = StudyDate(lesson_id=lesson_id, date=last_studied)
        db.session.add(study_date)
        db.session.commit()
        db_lesson.scheduled_for_today = False  # Reset the flag
        db.session.commit()
        return redirect(url_for('main.index'))
    elif request.method == 'GET':
        form.confidence_level.date = db_lesson.confidence_level
        form.notes.data = db_lesson.notes
    return render_template('lessons/update.html', lesson=db_lesson, lesson_details=lesson_details, datetime=datetime, form=form)

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
    today = datetime.today()
    lessons_from_csv = load_lessons_from_csv()
    revisions, new_lessons = get_daily_schedule(today)
    available_new_lessons = [lesson for lesson in lessons_from_csv if Lesson.query.filter_by(lesson_id=lesson['lesson_id'], confidence_level=0).first()]
    if request.method == 'POST':
        selected_lesson_id = request.form.get('selected_lesson')
        db_lesson = Lesson.query.filter_by(lesson_id=selected_lesson_id).first()
        if db_lesson:
            # Schedule the selected lesson for today
            db_lesson.scheduled_for_today = True
            db.session.commit()
            return redirect(url_for('schedule'))
    return render_template('schedule/schedule.html', revisions=revisions, new_lessons=new_lessons, available_new_lessons=available_new_lessons, datetime=datetime)

@bp.route('/topic/<topic_name>')
def view_topic(topic_name) -> render_template:
    """
    Display all lessons within a specific topic.
    """
    lessons_from_csv = load_lessons_from_csv()
    topic_lessons = []
    for lesson in lessons_from_csv:
        if lesson['topic'] == topic_name:
            db_lesson = Lesson.query.filter_by(lesson_id=lesson['lesson_id']).first()
            lesson_data = {
                'lesson_id': lesson['lesson_id'],
                'lesson_name': lesson['lesson_name'],
                'confidenc_level': db_lesson.confidence_level if db_lesson else 0,
                'next_review_date': db_lesson.next_review_date if db_lesson else None,
                'last_studied': db_lesson.last_studied if db_lesson else None,
                'notes': db_lesson.notes if db_lesson else ''
            }
            topic_lessons.append(lesson_data)
    return render_template('lessons/topic_lessons.html', topic_name=topic_name, lessons=topic_lessons, datetime=datetime)