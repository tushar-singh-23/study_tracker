from flask import Flask, render_template, request, redirect, url_for
from study_tracker.app.models import db, Lesson, StudyDate
from datetime import datetime, timedelta
import csv

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
# db = SQLAlchemy(app)
db.init_app(app)
migrate = Migrate(app, db)

# Load lessons from CSV
def load_lessons_from_csv():
    lessons = []
    with open('study_tracker/cfa_lessons.csv', newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            lesson_id = f"{row['Topic']}_{row['Lesson']}"
            lessons.append({
                'lesson_id': lesson_id,
                'topic': row['Topic'],
                'lesson_name': row['Lesson']
            })
    return lessons

# Ensure all lessons exist in the database
def initialize_lessons():
    lessons = load_lessons_from_csv()
    for lesson in lessons:
        existing_lesson = Lesson.query.filter_by(lesson_id=lesson['lesson_id']).first()
        if not existing_lesson:
            new_lesson = Lesson(
                lesson_id=lesson['lesson_id']
            )
            db.session.add(new_lesson)
    db.session.commit()

# Call this function when the app starts
with app.app_context():
    db.create_all()
    initialize_lessons()

def calculate_next_review_date(confidence_level, last_studied, previous_interval=1, previous_ease_factor=2.5):
    if confidence_level < 5:
        ease_factor = max(1.3, previous_ease_factor - 0.2)
        interval = 1
    else:
        ease_factor = previous_ease_factor + 0.1
        interval = previous_interval * ease_factor

    next_review_date = last_studied + timedelta(days=round(interval))
    return next_review_date, interval, ease_factor

def calculate_progress():
    lessons_from_csv = load_lessons_from_csv()
    topics = {}
    for lesson in lessons_from_csv:
        topic = lesson['topic']
        if topic not in topics:
            topics[topic] = {'total': 0, 'confidence_sum': 0}
        topics[topic]['total'] += 10  # Max confidence per lesson is 10
        db_lesson = Lesson.query.filter_by(lesson_id=lesson['lesson_id']).first()
        if db_lesson:
            topics[topic]['confidence_sum'] += db_lesson.confidence_level
    progress = {}
    for topic, data in topics.items():
        completion_percentage = (data['confidence_sum'] / data['total']) * 100 if data['total'] > 0 else 0
        progress[topic] = completion_percentage
    return progress

def get_daily_schedule(date):
    is_weekend = date.weekday() >= 5
    total_time = 3.5 if is_weekend else 2
    estimated_time_per_lesson = 0.1  # Estimated hours per lesson

    # Fetch overdue revisions
    overdue_revisions = Lesson.query.filter(Lesson.next_review_date < date).all()
    due_revisions = Lesson.query.filter(Lesson.next_review_date == date).all()
    revisions = overdue_revisions + due_revisions

    # Adjust time allocation
    revision_time = len(revisions) * estimated_time_per_lesson
    new_content_time = max(0, total_time - revision_time)

    # If revision time exceeds total time, focus on revisions
    if revision_time > total_time:
        revision_time = total_time
        new_content_time = 0

    # Fetch next new lesson from CSV
    new_lessons = []
    if new_content_time > 0:
        lessons_from_csv = load_lessons_from_csv()
        for lesson in lessons_from_csv:
            db_lesson = Lesson.query.filter_by(lesson_id=lesson['lesson_id']).first()
            if db_lesson and db_lesson.confidence_level == 0:
                new_lessons.append({'lesson_id': lesson['lesson_id'], 'topic': lesson['topic'], 'lesson_name': lesson['lesson_name']})
                break  # Only get the next lesson
    scheduled_new_lessons = Lesson.query.filter_by(scheduled_for_today=True).all()
    return revisions, scheduled_new_lessons

@app.route('/')
def index():
    lessons_from_csv = load_lessons_from_csv()
    progress = calculate_progress()
    lessons = []
    for csv_lesson in lessons_from_csv:
        db_lesson = Lesson.query.filter_by(lesson_id=csv_lesson['lesson_id']).first()
        if db_lesson:
            lesson_data = {
                'lesson_id': csv_lesson['lesson_id'],
                'topic': csv_lesson['topic'],
                'lesson_name': csv_lesson['lesson_name'],
                'confidence_level': db_lesson.confidence_level,
                'next_review_date': db_lesson.next_review_date,
                'last_studied': db_lesson.last_studied,
                'notes': db_lesson.notes
            }
            lessons.append(lesson_data)
    return render_template('index.html', lessons=lessons, progress=progress, datetime=datetime)


@app.route('/add_lesson', methods=['GET', 'POST'])
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
    return render_template('add_lesson.html')

@app.route('/update_lesson/<lesson_id>', methods=['GET', 'POST'])
def update_lesson(lesson_id):
    db_lesson = Lesson.query.filter_by(lesson_id=lesson_id).first_or_404()
    lesson_details = next((l for l in load_lessons_from_csv() if l['lesson_id'] == lesson_id), None)
    if request.method == 'POST':
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
        return redirect(url_for('schedule'))
    return render_template('update_lesson.html', lesson=db_lesson, lesson_details=lesson_details, datetime=datetime)


@app.route('/set_new_lesson', methods=['POST'])
def set_new_lesson():
    lesson_id = request.form.get('lesson_id')
    db_lesson = Lesson.query.filter_by(lesson_id=lesson_id).first()
    if db_lesson:
        # Add the lesson to today's new lessons
        pass  # Implement logic as needed
    return redirect(url_for('schedule'))

@app.route('/view_study_dates/<lesson_id>')
def view_study_dates(lesson_id):
    lesson = Lesson.query.filter_by(lesson_id=lesson_id).first_or_404()
    study_dates = StudyDate.query.filter_by(lesson_id=lesson_id).order_by(StudyDate.date.desc()).all()
    lesson_details = next((l for l in load_lessons_from_csv() if l['lesson_id'] == lesson_id), None)
    return render_template('view_study_dates.html', lesson=lesson, study_dates=study_dates, lesson_details=lesson_details)

@app.route('/schedule', methods=['GET', 'POST'])
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
    return render_template('schedule.html', revisions=revisions, new_lessons=new_lessons, available_new_lessons=available_new_lessons, datetime=datetime)

if __name__ == '__main__':
    app.run(debug=True)
