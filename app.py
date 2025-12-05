import os, json
from flask import Flask, render_template, redirect, url_for, request, flash, jsonify
from models import db, User, Event, Booking
from forms import EventForm
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from dotenv import load_dotenv
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from datetime import datetime
from flask import send_file
import io
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Spacer
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch
from datetime import datetime, date

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'devsecret')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('SQLALCHEMY_DATABASE_URI', 'sqlite:///database.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# ------------------ ACTIVITY LOGGER (no DB changes) ------------------
# location for log file (app root)
LOG_FILE = os.path.join(app.root_path, "activity.log")

ICON_MAP = {
    "register": "🟢",
    "login": "🔵",
    "logout": "⚪",
    "booking": "📝",
    "payment": "💰",
    "approve": "✅",
    "reject": "❌",
    "refunded": "💸",
    "event": "📅",
    "user": "👤",
    "other": "🔔"
}

def ensure_log_file():
    if not os.path.exists(LOG_FILE):
        # create empty file
        with open(LOG_FILE, "w", encoding="utf-8") as f:
            f.write("")

def log_activity(kind, text):
    """
    Write an activity line: ISO_DATETIME||KIND||TEXT
    kind should be one of ICON_MAP keys (or 'other').
    """
    ensure_log_file()
    ts = datetime.utcnow().isoformat()
    line = f"{ts}||{kind}||{text}\n"
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line)

def read_recent_activity(limit=20):
    """
    Read last `limit` lines and return list of dicts:
    { type, icon, text, time } with time in local human-readable form.
    """
    ensure_log_file()
    with open(LOG_FILE, "r", encoding="utf-8") as f:
        lines = [l.strip() for l in f if l.strip()]
    if not lines:
        return []
    last = lines[-limit:]
    items = []
    for ln in reversed(last):
        try:
            ts, kind, text = ln.split("||", 2)
            # parse ts to human friendly local time
            try:
                dt = datetime.fromisoformat(ts)
                timestr = dt.strftime("%d %b %Y, %I:%M %p")
            except Exception:
                timestr = ts
            icon = ICON_MAP.get(kind, ICON_MAP["other"])
            items.append({"type": kind, "icon": icon, "text": text, "time": timestr})
        except Exception:
            # fallback - put the whole line as text
            items.append({"type": "other", "icon": ICON_MAP["other"], "text": ln, "time": ""})
    return items
# --------------------------------------------------------------------

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def seed_events():
    if Event.query.count() == 0:
        samples = []
        def ad(d): return json.dumps(d)

        samples.extend([
            Event(
                name="Corporate Conference 2026",
                category="Business and Corporate",
                price=45000,
                available_days="Monday, Tuesday, Wednesday, Thursday",
                available_venues="Conference Hall A, Auditorium 2, Seminar Room 5, VIP Lounge, Sky Deck",
                available_dates=ad({
                    "Conference Hall A": ["2026-02-10", "2026-02-15", "2026-02-20", "2026-02-25", "2026-02-28"],
                    "Auditorium 2": ["2026-02-12", "2026-02-18", "2026-02-22", "2026-02-27", "2026-03-03"],
                    "Seminar Room 5": ["2026-02-11", "2026-02-19", "2026-02-23", "2026-02-29", "2026-03-04"],
                    "VIP Lounge": ["2026-02-14", "2026-02-22", "2026-02-26", "2026-03-02", "2026-03-06"],
                    "Sky Deck": ["2026-02-13", "2026-02-21", "2026-02-24", "2026-02-28", "2026-03-05"]
                })
            ),
            Event(
                name="Art & Craft Workshop",
                category="Workshops",
                price=5000,
                available_days="Saturday, Sunday",
                available_venues="Art Studio 1, Art Studio 2, Creative Hall, Open Garden, Gallery Room",
                available_dates=ad({
                    "Art Studio 1": ["2026-03-07", "2026-03-14", "2026-03-21", "2026-03-28", "2026-04-04"],
                    "Art Studio 2": ["2026-03-08", "2026-03-15", "2026-03-22", "2026-03-29", "2026-04-05"],
                    "Creative Hall": ["2026-03-09", "2026-03-16", "2026-03-23", "2026-03-30", "2026-04-06"],
                    "Open Garden": ["2026-03-10", "2026-03-17", "2026-03-24", "2026-03-31", "2026-04-07"],
                    "Gallery Room": ["2026-03-11", "2026-03-18", "2026-03-25", "2026-04-01", "2026-04-08"]
                })
            ),
            Event(
                name="Music Concert 2026",
                category="Entertainment",
                price=7500,
                available_days="Friday, Saturday, Sunday",
                available_venues="Open Arena, Grand Stage, Rooftop Hall, Auditorium 1, VIP Box",
                available_dates=ad({
                    "Open Arena": ["2026-04-10", "2026-04-17", "2026-04-24", "2026-05-01", "2026-05-08"],
                    "Grand Stage": ["2026-04-11", "2026-04-18", "2026-04-25", "2026-05-02", "2026-05-09"],
                    "Rooftop Hall": ["2026-04-12", "2026-04-19", "2026-04-26", "2026-05-03", "2026-05-10"],
                    "Auditorium 1": ["2026-04-13", "2026-04-20", "2026-04-27", "2026-05-04", "2026-05-11"],
                    "VIP Box": ["2026-04-14", "2026-04-21", "2026-04-28", "2026-05-05", "2026-05-12"]
                })
            ),
            Event(
                name="Tech Expo 2026",
                category="Technology",
                price=12000,
                available_days="Monday to Friday",
                available_venues="Expo Hall A, Expo Hall B, Innovation Center, Tech Arena, Conference Room 7",
                available_dates=ad({
                    "Expo Hall A": ["2026-05-05", "2026-05-10", "2026-05-15", "2026-05-20", "2026-05-25"],
                    "Expo Hall B": ["2026-05-06", "2026-05-11", "2026-05-16", "2026-05-21", "2026-05-26"],
                    "Innovation Center": ["2026-05-07", "2026-05-12", "2026-05-17", "2026-05-22", "2026-05-27"],
                    "Tech Arena": ["2026-05-08", "2026-05-13", "2026-05-18", "2026-05-23", "2026-05-28"],
                    "Conference Room 7": ["2026-05-09", "2026-05-14", "2026-05-19", "2026-05-24", "2026-05-29"]
                })
            ),
            Event(
                name="Food Festival",
                category="Food & Beverages",
                price=3000,
                available_days="Saturday, Sunday",
                available_venues="Main Courtyard, Open Grounds, Food Pavilion, Garden Area, Riverside Stage",
                available_dates=ad({
                    "Main Courtyard": ["2026-06-01", "2026-06-08", "2026-06-15", "2026-06-22", "2026-06-29"],
                    "Open Grounds": ["2026-06-02", "2026-06-09", "2026-06-16", "2026-06-23", "2026-06-30"],
                    "Food Pavilion": ["2026-06-03", "2026-06-10", "2026-06-17", "2026-06-24", "2026-07-01"],
                    "Garden Area": ["2026-06-04", "2026-06-11", "2026-06-18", "2026-06-25", "2026-07-02"],
                    "Riverside Stage": ["2026-06-05", "2026-06-12", "2026-06-19", "2026-06-26", "2026-07-03"]
                })
            ),
            Event(
                name="Photography Workshop",
                category="Workshops",
                price=6000,
                available_days="Wednesday, Thursday, Friday",
                available_venues="Studio 1, Studio 2, Outdoor Garden, Rooftop Deck, Conference Hall B",
                available_dates=ad({
                    "Studio 1": ["2026-07-05", "2026-07-12", "2026-07-19", "2026-07-26", "2026-08-02"],
                    "Studio 2": ["2026-07-06", "2026-07-13", "2026-07-20", "2026-07-27", "2026-08-03"],
                    "Outdoor Garden": ["2026-07-07", "2026-07-14", "2026-07-21", "2026-07-28", "2026-08-04"],
                    "Rooftop Deck": ["2026-07-08", "2026-07-15", "2026-07-22", "2026-07-29", "2026-08-05"],
                    "Conference Hall B": ["2026-07-09", "2026-07-16", "2026-07-23", "2026-07-30", "2026-08-06"]
                })
            ),
            Event(
                name="Yoga Retreat",
                category="Health & Wellness",
                price=10000,
                available_days="Monday to Sunday",
                available_venues="Wellness Hall, Garden Zone, Beach Side, Hilltop Pavilion, Indoor Studio",
                available_dates=ad({
                    "Wellness Hall": ["2026-08-01", "2026-08-05", "2026-08-10", "2026-08-15", "2026-08-20", "2026-08-25"],
                    "Garden Zone": ["2026-08-02", "2026-08-06", "2026-08-11", "2026-08-16", "2026-08-21", "2026-08-26"],
                    "Beach Side": ["2026-08-03", "2026-08-07", "2026-08-12", "2026-08-17", "2026-08-22", "2026-08-27"],
                    "Hilltop Pavilion": ["2026-08-04", "2026-08-08", "2026-08-13", "2026-08-18", "2026-08-23", "2026-08-28"],
                    "Indoor Studio": ["2026-08-05", "2026-08-09", "2026-08-14", "2026-08-19", "2026-08-24", "2026-08-29"]
                })
            ),
            Event(
                name="Science Fair",
                category="Education",
                price=4000,
                available_days="Tuesday, Wednesday, Thursday",
                available_venues="Science Lab 1, Science Lab 2, Auditorium 3, Open Arena, Tech Hall",
                available_dates=ad({
                    "Science Lab 1": ["2026-09-01", "2026-09-05", "2026-09-10", "2026-09-15", "2026-09-20"],
                    "Science Lab 2": ["2026-09-02", "2026-09-06", "2026-09-11", "2026-09-16", "2026-09-21"],
                    "Auditorium 3": ["2026-09-03", "2026-09-07", "2026-09-12", "2026-09-17", "2026-09-22"],
                    "Open Arena": ["2026-09-04", "2026-09-08", "2026-09-13", "2026-09-18", "2026-09-23"],
                    "Tech Hall": ["2026-09-05", "2026-09-09", "2026-09-14", "2026-09-19", "2026-09-24"]
                })
            ),
            Event(
                name="Book Fair",
                category="Education",
                price=2500,
                available_days="Saturday, Sunday",
                available_venues="Main Hall, Courtyard, Library, Open Ground, Exhibition Hall",
                available_dates=ad({
                    "Main Hall": ["2026-10-01", "2026-10-08", "2026-10-15", "2026-10-22", "2026-10-29"],
                    "Courtyard": ["2026-10-02", "2026-10-09", "2026-10-16", "2026-10-23", "2026-10-30"],
                    "Library": ["2026-10-03", "2026-10-10", "2026-10-17", "2026-10-24", "2026-10-31"],
                    "Open Ground": ["2026-10-04", "2026-10-11", "2026-10-18", "2026-10-25", "2026-11-01"],
                    "Exhibition Hall": ["2026-10-05", "2026-10-12", "2026-10-19", "2026-10-26", "2026-11-02"]
                })
            ),
            Event(
                name="Drama Festival",
                category="Entertainment",
                price=8000,
                available_days="Friday, Saturday",
                available_venues="Auditorium 1, Auditorium 2, Open Stage, Green Hall, Black Box Theater",
                available_dates=ad({
                    "Auditorium 1": ["2026-11-01", "2026-11-08", "2026-11-15", "2026-11-22", "2026-11-29"],
                    "Auditorium 2": ["2026-11-02", "2026-11-09", "2026-11-16", "2026-11-23", "2026-11-30"],
                    "Open Stage": ["2026-11-03", "2026-11-10", "2026-11-17", "2026-11-24", "2026-12-01"],
                    "Green Hall": ["2026-11-04", "2026-11-11", "2026-11-18", "2026-11-25", "2026-12-02"],
                    "Black Box Theater": ["2026-11-05", "2026-11-12", "2026-11-19", "2026-11-26", "2026-12-03"]
                })
            ),
            Event(
                name="Film Screening",
                category="Entertainment",
                price=3500,
                available_days="Thursday, Friday",
                available_venues="Cinema Hall 1, Cinema Hall 2, Open Roof, VIP Lounge, Media Hall",
                available_dates=ad({
                    "Cinema Hall 1": ["2026-12-01", "2026-12-05", "2026-12-10", "2026-12-15", "2026-12-20"],
                    "Cinema Hall 2": ["2026-12-02", "2026-12-06", "2026-12-11", "2026-12-16", "2026-12-21"],
                    "Open Roof": ["2026-12-03", "2026-12-07", "2026-12-12", "2026-12-17", "2026-12-22"],
                    "VIP Lounge": ["2026-12-04", "2026-12-08", "2026-12-13", "2026-12-18", "2026-12-23"],
                    "Media Hall": ["2026-12-05", "2026-12-09", "2026-12-14", "2026-12-19", "2026-12-24"]
                })
            ),
            Event(
                name="Charity Gala",
                category="Fundraiser",
                price=20000,
                available_days="Saturday",
                available_venues="Grand Ballroom, VIP Hall, Open Garden, Rooftop Terrace, Main Hall",
                available_dates=ad({
                    "Grand Ballroom": ["2026-12-05", "2026-12-12", "2026-12-19", "2026-12-26"],
                    "VIP Hall": ["2026-12-06", "2026-12-13", "2026-12-20", "2026-12-27"],
                    "Open Garden": ["2026-12-07", "2026-12-14", "2026-12-21", "2026-12-28"],
                    "Rooftop Terrace": ["2026-12-08", "2026-12-15", "2026-12-22", "2026-12-29"],
                    "Main Hall": ["2026-12-09", "2026-12-16", "2026-12-23", "2026-12-30"]
                })
            ),
            Event(
                name="Fashion Show",
                category="Entertainment",
                price=15000,
                available_days="Friday, Saturday",
                available_venues="Runway Hall, Grand Stage, VIP Lounge, Open Arena, Fashion Studio",
                available_dates=ad({
                    "Runway Hall": ["2026-09-01", "2026-09-08", "2026-09-15", "2026-09-22", "2026-09-29"],
                    "Grand Stage": ["2026-09-02", "2026-09-09", "2026-09-16", "2026-09-23", "2026-09-30"],
                    "VIP Lounge": ["2026-09-03", "2026-09-10", "2026-09-17", "2026-09-24", "2026-10-01"],
                    "Open Arena": ["2026-09-04", "2026-09-11", "2026-09-18", "2026-09-25", "2026-10-02"],
                    "Fashion Studio": ["2026-09-05", "2026-09-12", "2026-09-19", "2026-09-26", "2026-10-03"]
                })
            ),
            Event(
                name="Startup Meetup",
                category="Business and Corporate",
                price=7000,
                available_days="Wednesday, Thursday",
                available_venues="Innovation Hub, Conference Room 1, Networking Hall, Tech Arena, Sky Deck",
                available_dates=ad({
                    "Innovation Hub": ["2026-10-01", "2026-10-05", "2026-10-10", "2026-10-15", "2026-10-20"],
                    "Conference Room 1": ["2026-10-02", "2026-10-06", "2026-10-11", "2026-10-16", "2026-10-21"],
                    "Networking Hall": ["2026-10-03", "2026-10-07", "2026-10-12", "2026-10-17", "2026-10-22"],
                    "Tech Arena": ["2026-10-04", "2026-10-08", "2026-10-13", "2026-10-18", "2026-10-23"],
                    "Sky Deck": ["2026-10-05", "2026-10-09", "2026-10-14", "2026-10-19", "2026-10-24"]
                })
            ),
            Event(
                name="Marathon Event",
                category="Sports",
                price=1000,
                available_days="Sunday",
                available_venues="City Track, Riverside Track, Stadium Grounds, Park Arena, Beach Track",
                available_dates=ad({
                    "City Track": ["2026-11-01", "2026-11-08", "2026-11-15", "2026-11-22", "2026-11-29"],
                    "Riverside Track": ["2026-11-02", "2026-11-09", "2026-11-16", "2026-11-23", "2026-11-30"],
                    "Stadium Grounds": ["2026-11-03", "2026-11-10", "2026-11-17", "2026-11-24", "2026-12-01"],
                    "Park Arena": ["2026-11-04", "2026-11-11", "2026-11-18", "2026-11-25", "2026-12-02"],
                    "Beach Track": ["2026-11-05", "2026-11-12", "2026-11-19", "2026-11-26", "2026-12-03"]
                })
            ),
            Event(
                name="Culinary Workshop",
                category="Food & Beverages",
                price=4500,
                available_days="Friday, Saturday, Sunday",
                available_venues="Kitchen Lab 1, Kitchen Lab 2, Culinary Studio, Outdoor Pavilion, Main Hall",
                available_dates=ad({
                    "Kitchen Lab 1": ["2026-12-01", "2026-12-05", "2026-12-10", "2026-12-15", "2026-12-20"],
                    "Kitchen Lab 2": ["2026-12-02", "2026-12-06", "2026-12-11", "2026-12-16", "2026-12-21"],
                    "Culinary Studio": ["2026-12-03", "2026-12-07", "2026-12-12", "2026-12-17", "2026-12-22"],
                    "Outdoor Pavilion": ["2026-12-04", "2026-12-08", "2026-12-13", "2026-12-18", "2026-12-23"],
                    "Main Hall": ["2026-12-05", "2026-12-09", "2026-12-14", "2026-12-19", "2026-12-24"]
                })
            ),
            Event(
                name="Birthday Bash Package",
                category="Birthday",
                price=15000,
                available_days="Monday, Tuesday, Wednesday, Thursday, Friday, Saturday, Sunday",
                available_venues="Banquet Hall A, Garden Venue, Rooftop Party Area, Club Lounge, Poolside",
                available_dates=json.dumps({
                    "Banquet Hall A": ["2026-01-03", "2026-01-10", "2026-01-17", "2026-01-24", "2026-01-31"],
                    "Garden Venue": ["2026-01-04", "2026-01-11", "2026-01-18", "2026-01-25", "2026-02-01"],
                    "Rooftop Party Area": ["2026-01-05", "2026-01-12", "2026-01-19", "2026-01-26", "2026-02-02"],
                    "Club Lounge": ["2026-01-06", "2026-01-13", "2026-01-20", "2026-01-27", "2026-02-03"],
                    "Poolside": ["2026-01-07", "2026-01-14", "2026-01-21", "2026-01-28", "2026-02-04"]
                })
            ),
        ])

        db.session.add_all(samples)
        db.session.commit()


@app.before_request
def create_tables():
    db.create_all()
    if not User.query.filter_by(email='admin@events.local').first():
        admin = User(name='Admin', email='admin@events.local', password=bcrypt.generate_password_hash('admin123').decode('utf-8'), is_admin=True)
        db.session.add(admin)
        db.session.commit()
    seed_events()
    ensure_log_file()

def attach_upcoming_status(bookings):
    today = date.today()
    for booking in bookings:
        try:
            event_date = datetime.strptime(booking.date, '%Y-%m-%d').date()
            booking.is_upcoming = event_date >= today
        except Exception:
            booking.is_upcoming = False
    return bookings

@app.route('/')
def home():
    selected_category = request.args.get('category','').strip()
    if selected_category:
        events = Event.query.filter_by(category=selected_category).all()
    else:
        events = Event.query.all()
    categories = [c[0] for c in db.session.query(Event.category).distinct().all()]
    return render_template('home.html', events=events, categories=categories, selected_category=selected_category)

@app.route('/register', methods=['GET','POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        pw = request.form['password']
        if User.query.filter_by(email=email).first():
            flash('Email already registered', 'warning')
            return redirect(url_for('register'))
        hashed = bcrypt.generate_password_hash(pw).decode('utf-8')
        user = User(name=name, email=email, password=hashed)
        db.session.add(user)
        db.session.commit()

        # log registration
        log_activity("register", f"New registration: {name} ({email})")

        flash('Registered! Please login.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        pw = request.form['password']
        user = User.query.filter_by(email=email).first()
        if user and bcrypt.check_password_hash(user.password, pw):
            login_user(user)
            user.last_login = datetime.utcnow()
            db.session.commit()

            # log login
            log_activity("login", f"User logged in: {user.name} ({user.email})")

            flash('Logged in successfully', 'success')
            return redirect(url_for('user_dashboard') if not user.is_admin else url_for('admin_dashboard'))
        flash('Invalid credentials', 'danger')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    # log logout
    log_activity("logout", f"User logged out: {current_user.name} ({current_user.email})")

    logout_user()
    flash('Logged out', 'info')
    return redirect(url_for('home'))

@app.route('/events/<int:event_id>')
def event_detail(event_id):
    event = Event.query.get_or_404(event_id)
    available_dates = {}
    try:
        available_dates = json.loads(event.available_dates or "{}")
    except Exception:
        available_dates = {}
    return render_template('event_detail.html', event=event, available_dates=available_dates)

@app.route('/book/<int:event_id>', methods=['GET','POST'])
@login_required
def book_event(event_id):
    import json as _json
    event = Event.query.get_or_404(event_id)
    try:
        av = _json.loads(event.available_dates or "{}")
    except:
        av = {}
    venues = list(av.keys())
    if request.method == 'POST':
        date = request.form['date']
        venue = request.form['venue']
        day = request.form.get('day', '')
        booking = Booking(user_id=current_user.id, event_id=event.id, date=date, venue=venue, day=day)
        db.session.add(booking)
        db.session.commit()

        # log booking creation
        log_activity("booking", f"{current_user.name} created booking #{booking.id} for {event.name} on {date} at {venue}")

        flash('Booking created and is pending payment + admin approval.', 'info')
        return redirect(url_for('user_dashboard'))
    return render_template('booking.html', event=event, venues=venues, available_dates=av)

@app.route('/user/dashboard')
@login_required
def user_dashboard():
    bookings = Booking.query.filter_by(user_id=current_user.id).all()
    bookings = attach_upcoming_status(bookings)
    return render_template('user_dashboard.html', bookings=bookings)

@app.route('/pay/<int:booking_id>', methods=['GET'])
@login_required
def pay(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    if booking.user_id != current_user.id:
        flash('Not allowed', 'danger')
        return redirect(url_for('user_dashboard'))
    return render_template('fake_razorpay.html', booking=booking)

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        new_pw = request.form.get('new_password')
        confirm_pw = request.form.get('confirm_password')

        if new_pw != confirm_pw:
            flash('New passwords do not match.', 'warning')
            return redirect(url_for('profile'))

        hashed_password = bcrypt.generate_password_hash(new_pw).decode('utf-8')
        current_user.password = hashed_password
        db.session.commit()
        
        flash('Your password has been updated successfully!', 'success')
        return redirect(url_for('profile'))

    # ---------- STATS ----------
    total_bookings = Booking.query.filter_by(user_id=current_user.id).count()
    paid_bookings = Booking.query.filter_by(user_id=current_user.id, paid=True).count()
    upcoming = Booking.query.filter(
        Booking.user_id == current_user.id,
        Booking.date >= datetime.now().strftime("%Y-%m-%d")
    ).count()

    # ---------- ACTIVITY LOG ----------
    activity_log = Booking.query.filter_by(user_id=current_user.id) \
                                .order_by(Booking.created_at.desc()) \
                                .limit(10).all()

    return render_template(
        'profile.html',
        user=current_user,
        total_bookings=total_bookings,
        paid_bookings=paid_bookings,
        upcoming=upcoming,
        activity_log=activity_log
    )
    
################################################
@app.route('/payment_complete', methods=['POST'])
@login_required
def payment_complete():
    booking_id = int(request.form['booking_id'])
    # Get the method selected from the radio buttons
    payment_method = request.form.get('payment_method', 'CARD').upper() 
    
    booking = Booking.query.get_or_404(booking_id)
    
    if booking.user_id != current_user.id:
        flash('Not allowed', 'danger')
        return redirect(url_for('user_dashboard'))
    
    booking.paid = True
    # Create a reference based on the method chosen
    booking.payment_reference = f"FAKE-{payment_method}-{booking.id:06d}"
    
    db.session.commit()

    # log payment
    log_activity("payment", f"{current_user.name} paid for booking #{booking.id} ({booking.payment_reference}) via {payment_method}")

    flash(f'Payment successful via {payment_method}. Waiting for admin approval.', 'success')
    return redirect(url_for('user_dashboard'))


################################################
@app.route('/admin/login', methods=['GET','POST'])
def admin_login():
    if request.method == 'POST':
        email = request.form['email']
        pw = request.form['password']
        user = User.query.filter_by(email=email, is_admin=True).first()
        if user and bcrypt.check_password_hash(user.password, pw):
            login_user(user)

            # log admin login
            log_activity("login", f"ADMIN logged in: {user.name} ({user.email})")

            flash('Admin logged in', 'success')
            return redirect(url_for('admin_dashboard'))
        flash('Invalid admin credentials', 'danger')
    return render_template('admin_login.html')

################################################

@app.route('/admin/dashboard')
def admin_dashboard():
    if not current_user.is_authenticated or not current_user.is_admin:
        flash('Admin access only', 'danger')
        return redirect(url_for('home'))
    events = Event.query.all()
    bookings = Booking.query.order_by(Booking.id.desc()).all()
    bookings = attach_upcoming_status(bookings)
    
    return render_template('admin_dashboard.html', events=events, bookings=bookings)

################################################

@app.route('/admin/events')
def admin_events():
    if not current_user.is_authenticated or not current_user.is_admin:
        flash('Admin access only', 'danger')
        return redirect(url_for('home'))
    q = request.args.get('search','').strip()
    events_q = Event.query
    if q:
        events_q = events_q.filter(Event.name.ilike(f'%{q}%'))
    events = events_q.order_by(Event.id.desc()).all()
    return render_template('admin_events.html', events=events, search=q)

@app.route('/admin/users')
@login_required
def admin_users():
    if not current_user.is_admin:
        return redirect(url_for('home'))

    search = request.args.get("search", "").strip()
    date_from = request.args.get("date_from", "")
    date_to = request.args.get("date_to", "")

    # Only non-admin users
    query = User.query.filter_by(is_admin=False)

    if search:
        query = query.filter(
            (User.name.ilike(f"%{search}%")) |
            (User.email.ilike(f"%{search}%"))
        )

    if date_from:
        query = query.filter(User.created_at >= date_from)
    if date_to:
        query = query.filter(User.created_at <= date_to)

    users = query.order_by(User.id.desc()).all()
    total_users = len(users)

    return render_template(
        "admin_users.html",
        users=users,
        total_users=total_users,
        search=search,
        date_from=date_from,
        date_to=date_to
    )
################################################

@app.route("/admin/activity")
def admin_activity():
    if not current_user.is_authenticated or not current_user.is_admin:
        flash('Admin access only', 'danger')
        return redirect(url_for('home'))
    # render page built from activity.log
    activity = read_recent_activity(100)
    return render_template('activity_page.html', activity=activity)

@app.route("/stats")
@login_required
def stats_page():
    # Total users
    total_users = User.query.count()

    # Active today: users whose last_login date == today
    today = date.today()
    active_today = 0
    if hasattr(User, 'last_login'):
        active_today = User.query.filter(
            db.func.date(User.last_login) == today
        ).count()

    # New signups today
    new_signups = 0
    if hasattr(User, 'created_at'):
        new_signups = User.query.filter(
            db.func.date(User.created_at) == today
        ).count()

    # Total revenue: sum of event.price for paid bookings
    total_revenue = db.session.query(
        db.func.coalesce(db.func.sum(Event.price), 0)
    ).join(Booking, Booking.event_id == Event.id).filter(Booking.paid == True).scalar() or 0

    # Recent activity — read from activity.log
    activity = read_recent_activity(20)

    return render_template(
        "stats.html",
        total_users=total_users,
        active_today=active_today,
        new_signups=new_signups,
        total_revenue=int(total_revenue),
        activity=activity
    )

@app.route("/api/stats")
@login_required
def api_stats():
    today = date.today()
    total_users = User.query.count()
    active_today = User.query.filter(db.func.date(User.last_login) == today).count() if hasattr(User, 'last_login') else 0
    new_signups = User.query.filter(db.func.date(User.created_at) == today).count() if hasattr(User, 'created_at') else 0
    total_revenue = db.session.query(db.func.coalesce(db.func.sum(Event.price), 0)).join(Booking, Booking.event_id == Event.id).filter(Booking.paid == True).scalar() or 0

    # activity as JSON built from activity.log
    recent_logs = read_recent_activity(20)
    activity_json = [{
        "icon": it["icon"],
        "text": it["text"],
        "time": it["time"]
    } for it in recent_logs]

    return jsonify({
        "total_users": total_users,
        "active_today": active_today,
        "new_signups": new_signups,
        "total_revenue": int(total_revenue),
        "activity": activity_json
    })

# --- admin add/edit/delete events: log these actions (optional) ---
@app.route('/admin/event/add', methods=['GET','POST'])
def admin_add_event():
    if not current_user.is_authenticated or not current_user.is_admin:
        flash('Admin access only', 'danger')
        return redirect(url_for('home'))
    form = EventForm()
    if form.validate_on_submit():
        ed = form.available_dates.data.strip()
        event = Event(name=form.name.data.strip(), category=form.category.data.strip(), price=form.price.data, available_days=form.available_days.data.strip(), available_venues=form.available_venues.data.strip(), available_dates=ed)
        db.session.add(event)
        db.session.commit()

        log_activity("event", f"Event added: {event.name} by {current_user.name}")

        flash('Event added', 'success')
        return redirect(url_for('admin_events'))
    return render_template('add_event.html', form=form)

@app.route('/admin/event/edit/<int:event_id>', methods=['GET','POST'])
def admin_edit_event(event_id):
    if not current_user.is_authenticated or not current_user.is_admin:
        flash('Admin access only', 'danger')
        return redirect(url_for('home'))
    event = Event.query.get_or_404(event_id)
    form = EventForm(obj=event)
    if request.method == 'GET':
        form.available_dates.data = event.available_dates or '{}'
    if form.validate_on_submit():
        old_name = event.name
        event.name = form.name.data.strip()
        event.category = form.category.data.strip()
        event.price = form.price.data
        event.available_days = form.available_days.data.strip()
        event.available_venues = form.available_venues.data.strip()
        event.available_dates = form.available_dates.data.strip()
        db.session.commit()

        log_activity("event", f"Event edited: {old_name} -> {event.name} by {current_user.name}")

        flash('Event updated', 'success')
        return redirect(url_for('admin_events'))
    return render_template('edit_event.html', form=form, event=event)

@app.route('/admin/event/delete/<int:event_id>', methods=['POST'])
def admin_delete_event(event_id):
    if not current_user.is_authenticated or not current_user.is_admin:
        flash('Admin access only', 'danger')
        return redirect(url_for('home'))
    event = Event.query.get_or_404(event_id)
    name = event.name
    db.session.delete(event)
    db.session.commit()

    log_activity("event", f"Event deleted: {name} by {current_user.name}")

    flash('Event deleted', 'info')
    return redirect(url_for('admin_events'))

@app.route('/admin/approve/<int:booking_id>', methods=['GET'])
def admin_approve(booking_id):
    if not current_user.is_authenticated or not current_user.is_admin:
        flash('Admin access only', 'danger')
        return redirect(url_for('home'))
    booking = Booking.query.get_or_404(booking_id)
    booking.status = 'Approved'
    db.session.commit()

    # log approval with payment info
    log_activity("approve", f"Booking #{booking.id} APPROVED by admin. User: {booking.user.email}. Paid: {'Yes' if booking.paid else 'No'}. Ref: {booking.payment_reference or '-'}")

    flash('Booking approved', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/reject/<int:booking_id>', methods=['POST', 'GET'])
def admin_reject(booking_id):
    if not current_user.is_authenticated or not current_user.is_admin:
        flash('Admin access only', 'danger')
        return redirect(url_for('home'))

    booking = Booking.query.get_or_404(booking_id)

    # Accept optional reason
    reason = request.form.get('reason', '').strip()
    if not reason:
        reason = "Your booking was rejected by the admin."

    # capture previous payment info for logging
    previously_paid = booking.paid
    prev_ref = booking.payment_reference

    booking.status = 'Rejected'
    booking.rejection_reason = reason

    # Prevent user from paying for a rejected booking / mark refunded semantics
    if previously_paid:
        # We keep an audit via the log; in DB we set paid False and clear payment_reference
        booking.paid = False
        booking.payment_reference = None
        db.session.commit()

        log_activity("reject", f"Booking #{booking.id} REJECTED by admin. Reason: {reason}. Previously paid: Yes. Refunded (simulated). PrevRef: {prev_ref}")
        # also a separate refunded entry
        log_activity("refunded", f"Refund simulated for booking #{booking.id} (user {booking.user.email}) amount ₹{booking.event.price:.2f}")
    else:
        db.session.commit()
        log_activity("reject", f"Booking #{booking.id} REJECTED by admin. Reason: {reason}. Previously paid: No.")

    flash('Booking has been rejected.', 'info')
    return redirect(url_for('admin_dashboard'))

@app.route('/_validate_dates', methods=['POST'])
def _validate_dates():
    import json as _json
    text = request.form.get('text','')
    try:
        parsed = _json.loads(text)
        if not isinstance(parsed, dict):
            return jsonify({'ok':False, 'error':'JSON must be an object mapping venue->dates list'})
        for k,v in parsed.items():
            if not isinstance(v, list):
                return jsonify({'ok':False, 'error':'Each venue must map to a list of date strings'})
        return jsonify({'ok':True})
    except Exception as e:
        return jsonify({'ok':False, 'error': str(e)})

@app.route("/download_receipt/<int:booking_id>")
@login_required
def download_receipt(booking_id):
    booking = Booking.query.get_or_404(booking_id)

    if booking.user_id != current_user.id:
        flash("Unauthorized access!", "danger")
        return redirect(url_for("user_dashboard"))

    if not booking.paid or booking.status != 'Approved':
        flash("You can download receipt only after payment.", "warning")
        return redirect(url_for("user_dashboard"))

    # (receipt generation unchanged)
    buffer = io.BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=40, leftMargin=40,
        topMargin=60, bottomMargin=40
    )

    styles = getSampleStyleSheet()
    normal = styles["Normal"]
    normal.fontName = "Helvetica"
    normal.fontSize = 11
    normal.leading = 14

    PRIMARY = colors.HexColor("#5b2c6f")
    DARKGREY = colors.HexColor("#2c2c2c")
    LIGHTGREY = colors.HexColor("#f2f2f2")

    title_style = ParagraphStyle(
        name="TitleStyle",
        fontName="Helvetica-Bold",
        fontSize=22,
        leading=26,
        textColor=PRIMARY,
        alignment=1,
        spaceAfter=20
    )

    section_title = ParagraphStyle(
        name="SectionTitle",
        fontName="Helvetica-Bold",
        fontSize=14,
        textColor=PRIMARY,
        spaceAfter=10
    )

    story = []
    story.append(Paragraph("Prestige Planners – Payment Receipt", title_style))
    story.append(Spacer(1, 10))

    invoice_info_data = [
        ["Receipt No.:", f"#{booking.id}"],
        ["Generated On:", datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
        ["Payment Ref:", booking.payment_reference]
    ]

    invoice_table = Table(invoice_info_data, colWidths=[120, 350])
    invoice_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), LIGHTGREY),
        ('TEXTCOLOR', (0, 0), (-1, -1), DARKGREY),
        ('BOX', (0, 0), (-1, -1), 1, colors.grey),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
    ]))

    story.append(invoice_table)
    story.append(Spacer(1, 20))

    story.append(Paragraph("Customer Details", section_title))
    customer_data = [
        ["Name:", booking.user.name],
        ["Email:", booking.user.email],
    ]
    cust_table = Table(customer_data, colWidths=[120, 350])
    cust_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.white),
        ('TEXTCOLOR', (0, 0), (-1, -1), DARKGREY),
        ('BOX', (0, 0), (-1, -1), 1, colors.grey),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
    ]))

    story.append(cust_table)
    story.append(Spacer(1, 20))

    story.append(Paragraph("Event Details", section_title))
    event_data = [
        ["Event Name:", booking.event.name],
        ["Venue:", booking.venue],
        ["Selected Date:", booking.date],
    ]
    event_table = Table(event_data, colWidths=[120, 350])
    event_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.white),
        ('TEXTCOLOR', (0, 0), (-1, -1), DARKGREY),
        ('BOX', (0, 0), (-1, -1), 1, colors.grey),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
    ]))

    story.append(event_table)
    story.append(Spacer(1, 25))

    story.append(Paragraph("Payment Summary", section_title))
    price_data = [
        ["Description", "Amount (Rs.)"],
        [
            Paragraph(f"{booking.event.name} Booking Fee", normal),
            Paragraph(f"{booking.event.price:.2f}", normal)
        ]
    ]
    price_table = Table(price_data, colWidths=[350, 120])
    price_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), PRIMARY),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), "Helvetica-Bold"),
        ('BACKGROUND', (0, 1), (-1, -1), LIGHTGREY),
        ('TEXTCOLOR', (0, 1), (-1, -1), DARKGREY),
        ('ALIGN', (1, 1), (1, -1), 'RIGHT'),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ('RIGHTPADDING', (0, 0), (-1, -1), 10),
        ('BOX', (0, 0), (-1, -1), 1, colors.grey),
        ('INNERGRID', (0, 0), (-1, -1), 0.25, colors.grey),
        ('NOSPLIT', (0, 0), (-1, -1)),
    ]))

    story.append(price_table)
    story.append(Spacer(1, 35))

    thank_style = ParagraphStyle(
        name="Thanks",
        fontName="Helvetica-Oblique",
        fontSize=12,
        textColor=PRIMARY,
        alignment=1,
    )
    story.append(Paragraph("Thank you for choosing Prestige Planners!", thank_style))

    doc.build(story)

    buffer.seek(0)
    return send_file(
        buffer,
        as_attachment=True,
        download_name=f"receipt_{booking.id}.pdf",
        mimetype="application/pdf"
    )

if __name__ == '__main__':
    app.run(debug=True)
