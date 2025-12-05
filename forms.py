from flask_wtf import FlaskForm
from wtforms import StringField, FloatField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Length, NumberRange

class EventForm(FlaskForm):
    name = StringField('Event Name', validators=[DataRequired(), Length(min=2, max=200)])
    category = StringField('Category', validators=[DataRequired(), Length(min=2, max=100)])
    price = FloatField('Price', validators=[DataRequired(), NumberRange(min=0.0, message='Price must be >= 0')])
    available_days = StringField('Available Days', validators=[DataRequired(), Length(min=3, max=200)])
    available_venues = StringField('Available Venues', validators=[DataRequired(), Length(min=3, max=400)])
    available_dates = TextAreaField('Available Dates (JSON mapping venue -> [dates])', validators=[DataRequired(), Length(min=2, max=2000)])
    submit = SubmitField('Save Event')
