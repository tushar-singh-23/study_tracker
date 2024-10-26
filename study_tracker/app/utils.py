import csv
from datetime import datetime, timedelta
from app.models import Lesson

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