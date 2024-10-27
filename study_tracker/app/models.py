from datetime import datetime
from app import db

class Lesson(db.Model):
    """Model representing a lesson."""
    id = db.Column(db.Integer, primary_key=True)
    lesson_id = db.Column(db.String(100), unique=True, nullable=False)
    confidence_level = db.Column(db.Integer, default=0)
    last_studied = db.Column(db.Date)
    next_review_date = db.Column(db.Date)
    interval = db.Column(db.Integer, default=1)
    ease_factor = db.Column(db.Float, default=2.5)
    notes = db.Column(db.Text)
    scheduled_for_today = db.Column(db.Boolean, default=False)
    # Relationship to StudyDate
    study_dates = db.relationship('StudyDate', backref='lesson', lazy='dynamic')

class StudyDate(db.Model):
    """Model representing a study session for a lesson."""
    id = db.Column(db.Integer, primary_key=True)
    lesson_id = db.Column(db.String(100), db.ForeignKey('lesson.lesson_id'), nullable=False)
    date = db.Column(db.Date, default=datetime.utcnow().date)
    study_time = db.Column(db.Integer, default=60)  # Study time in minutes
    notes = db.Column(db.Text)

class UserSettings(db.Model):
    """Model representing user-specific settings"""
    id = db.Column(db.Integer, primary_key=True)
    total_study_time_weekday = db.Column(db.Float, default=2.0) # Hours
    total_study_time_weekend = db.Column(db.Float, default=3.5) # Hours
    completion_date = db.Column(db.Date)
