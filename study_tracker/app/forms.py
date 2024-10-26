from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField, TextAreaField, SubmitField
from wtforms.validators import DataRequired, NumberRange

class UpdateLessonForm(FlaskForm):
    confidence_level = IntegerField('Confidence Level (1-10)', validators=[DataRequired(), NumberRange(min=1, max=10)])
    notes = TextAreaField('Notes')
    submit = SubmitField('Save')
