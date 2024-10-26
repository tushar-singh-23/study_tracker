
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






