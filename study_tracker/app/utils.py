import csv
from datetime import datetime, timedelta
from app import db
from app.models import Lesson, UserSettings, StudyDate
from sqlalchemy.sql import func

# Load lessons from CSV
def load_lessons_from_csv():
    lessons = []
    with open('cfa_lessons.csv', newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            lesson_id = f"{row['Topic']}_{row['Lesson']}"
            lessons.append({
                'lesson_id': lesson_id,
                'topic': row['Topic'],
                'lesson_name': row['Lesson']
            })
    return lessons

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
    """Calculate the completion percentage for each topic.

    Returns:
        Dict[str, float]: A dictionary mapping topics to their completion percentages.
    """
    lessons_from_csv = load_lessons_from_csv()
    topics = {}
    for lesson in lessons_from_csv:
        topic = lesson['topic']
        if topic not in topics:
            topics[topic] = {'total_lessons': 0, 'completed_lessons': 0}
        topics[topic]['total_lessons'] += 1
        db_lesson = Lesson.query.filter_by(lesson_id=lesson['lesson_id']).first()
        if db_lesson and db_lesson.confidence_level > 0:
            topics[topic]['completed_lessons'] += 1
    progress = {}
    for topic, data in topics.items():
        completion_percentage = (data['completed_lessons'] / data['total_lessons']) * 100
        progress[topic] = {
            'completion_percentage': completion_percentage,
            'total_lessons': data['total_lessons'],
            'completed_lessons': data['completed_lessons']
        }
    return progress

def get_daily_schedule(date):
    """Get the daily schedule for a given date."""
    # Fetch user settings.
    settings = UserSettings.query.first()
    total_study_time = settings.total_study_time_weekend if date.weekday() >= 5 else settings.total_study_time_weekday # Saturday = 5, Sunday = 6

    # Fetch overdue and due revisions
    overdue_revisions = Lesson.query.filter(Lesson.next_review_date < date).all()
    due_revisions = Lesson.query.filter(Lesson.next_review_date == date).all()
    revisions = overdue_revisions + due_revisions

    # Sort lessons by priority (e.g., earliest next_review_date)
    revisions.sort(key=lambda x: x.next_review_date or date)

    # Estimate the total time required for revisions
    total_revision_tims = sum(
        db.session.query(func.avg(StudyDate.study_time)).filter_by(lesson_id=lesson.lesson_id).scalar() or 60
        for lesson in revisions
    ) / 60 # Convert minutes to hours

    # Suggest lessons based on available study time
    suggested_revisions = []
    accumulated_time = 0
    for lesson in revisions:
        avg_time = db.session.query(func.avg(StudyDate.study_time)).filter_by(lesson_id=lesson.lesson_id).scalar() or 60
        avg_time_hours = avg_time / 60
        if accumulated_time + avg_time_hours <= total_study_time:
            suggested_revisions.append(lesson)
            accumulated_time += avg_time_hours
        else:
            break

    # Fetch scheduled new lessons
    scheduled_new_lessons = Lesson.query.filter_by(scheduled_for_today=True).all()
    return suggested_revisions, scheduled_new_lessons

def calculate_study_plan(date):
    """Calculate study suggestions based on completion date."""
    settings = UserSettings.query.first()
    if not settings.completion_date:
        return {}
    
    # Calculate remaining days
    remaining_days = (settings.completion_date - date).days
    if remaining_days <= 0:
        return {'time_to': 'revise'}
    
    # Caculate remaining lessons
    total_lessons = Lesson.query.count()
    completed_lessons = Lesson.query.filter(Lesson.confidence_level >= 8).count()
    remaining_lessons = total_lessons - completed_lessons

    # Estimate total remaining study time (in hours)
    avg_study_time = db.session.query(func.avg(StudyDate.study_time)).scalar() or 60
    total_remaining_time = (remaining_lessons * avg_study_time) / 60

    # Calculate daily study time needed
    daily_study_time_needed = total_remaining_time / remaining_days

    # Suggest topics to study
    lessons_from_csv = load_lessons_from_csv()
    remaining_lessons_list = Lesson.query.filter(Lesson.confidence_level < 8).all()
    suggested_lessons = []
    accumulated_time = 0
    for lesson in remaining_lessons_list:
        if accumulated_time >= daily_study_time_needed:
            break
        avg_time = db.session.query(func.avg(StudyDate.study_time)).filter_by(lesson_id=lesson.lesson_id).scalar() or 60
        avg_time_hours = avg_time / 60
        accumulated_time += avg_time_hours
        # Get lesson details
        csv_lesson = next((l for l in lessons_from_csv if l['lesson_id'] == lesson.lesson_id), None)
        if csv_lesson:
            lesson.lesson_name = csv_lesson['lesson_name']
            lesson.topic = csv_lesson['topic']
            suggested_lessons.append(lesson)

    return {
        'daily_study_time_needed': daily_study_time_needed,
        'suggested_lessons': suggested_lessons
    }

# Ensure all lessons exist in the database
def initialize_lessons(db):
    lessons = load_lessons_from_csv()
    for lesson in lessons:
        existing_lesson = Lesson.query.filter_by(lesson_id=lesson['lesson_id']).first()
        if not existing_lesson:
            new_lesson = Lesson(
                lesson_id=lesson['lesson_id']
            )
            db.session.add(new_lesson)
    db.session.commit()