from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime, date

db = SQLAlchemy()

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(200), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    # use DateTime for created_at so we can filter by date/time easily
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    # last_login to track if user was active today
    last_login = db.Column(db.DateTime, nullable=True)

    bookings = db.relationship('Booking', backref='user', lazy=True)

    def __repr__(self):
        return f'<User {self.email}>'

class Event(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    category = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Float, default=0.0)
    available_days = db.Column(db.String(200), nullable=True)
    available_venues = db.Column(db.String(400), nullable=True)
    available_dates = db.Column(db.Text, nullable=True)  # JSON stored as text
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    bookings = db.relationship('Booking', backref='event', lazy=True)

    def __repr__(self):
        return f'<Event {self.name}>'

class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    event_id = db.Column(db.Integer, db.ForeignKey('event.id'), nullable=False)
    date = db.Column(db.String(100), nullable=False)
    venue = db.Column(db.String(200), nullable=True)
    day = db.Column(db.String(100), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(50), default='Pending')  # Pending/Approved/Rejected
    paid = db.Column(db.Boolean, default=False)
    payment_reference = db.Column(db.String(200), nullable=True)
    rejection_reason = db.Column(db.String(255), nullable=True)


    def __repr__(self):
        return f'<Booking {self.id}>'
