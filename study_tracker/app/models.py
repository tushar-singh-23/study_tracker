from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from . import db

class Lesson(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    lesson_id = db.Column(db.String(100), nullable=False, unique=True)  # Unique ID from CSV
    confidence_level = db.Column(db.Integer, default=0)
    last_studied = db.Column(db.Date)
    next_review_date = db.Column(db.Date)
    interval = db.Column(db.Integer, default=1)
    ease_factor = db.Column(db.Float, default=2.5)
    notes = db.Column(db.Text)
    study_dates = db.relationship('StudyDate', backref='lesson', lazy=True)
    scheduled_for_today = db.Column(db.Boolean, default=False)

class StudyDate(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    lesson_id = db.Column(db.String(100), db.ForeignKey('lesson.lesson_id'), nullable=False)
    date = db.Column(db.Date, default=datetime.today)
