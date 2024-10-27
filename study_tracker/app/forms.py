from flask_wtf import FlaskForm
from wtforms import IntegerField, TextAreaField, SubmitField, FloatField, DateField
from wtforms.validators import DataRequired, NumberRange

class UpdateLessonForm(FlaskForm):
    confidence_level = IntegerField('Confidence Level (1-10)', validators=[DataRequired(), NumberRange(min=1, max=10)])
    study_time = IntegerField('Study Time (minutes)', default=60, validators=[DataRequired(), NumberRange(min=1)])
    notes = TextAreaField('Notes')
    submit = SubmitField('Save')

class UserSettingsForm(FlaskForm):
    total_study_time_weekday = FloatField('Total Study Time on Weekdays (hours)', validators=[DataRequired(), NumberRange(min=0)])
    total_study_time_weekend = FloatField('Total Study Time on Weekends (hours)', validators=[DataRequired(), NumberRange(min=0)])
    completion_date = DateField('Completion Date', format='%Y-%m-%d', validators=[DataRequired()])
    submit = SubmitField('Save')