import os
from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'super_secret_key')  # Use environment variable for production
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///vehicle_rental.db')
db = SQLAlchemy(app)

# Database Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    bookings = db.relationship('Booking', backref='user', lazy=True)

class Vehicle(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    type = db.Column(db.String(100), nullable=False)
    registration = db.Column(db.String(100), unique=True, nullable=False)
    available = db.Column(db.Boolean, default=True)
    bookings = db.relationship('Booking', backref='vehicle', lazy=True)

class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    vehicle_id = db.Column(db.Integer, db.ForeignKey('vehicle.id'), nullable=False)

# Decorator to protect routes
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in to access this page.", "error")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function

# Routes
@app.route("/")
@app.route("/home")
def home() -> str:
    vehicles = Vehicle.query.all()
    return render_template("home.html", vehicles=vehicles)

@app.route("/register", methods=["GET", "POST"])
def register() -> str:
    if request.method == "POST":
        username = request.form["username"]
        password = generate_password_hash(request.form["password"], method="pbkdf2:sha256")
        
        if User.query.filter_by(username=username).first():
            flash("Username already exists!", "error")
            return redirect(url_for("register"))
        
        new_user = User(username=username, password=password)
        db.session.add(new_user)
        db.session.commit()
        
        flash("Registration successful! Please log in.", "success")
        return redirect(url_for("login"))
    
    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login() -> str:
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            session["user_id"] = user.id
            flash("Login successful!", "success")
            return redirect(url_for("home"))
        flash("Invalid credentials!", "error")
    return render_template("login.html")

@app.route("/logout")
def logout() -> str:
    session.pop("user_id", None)
    flash("Logged out successfully!", "info")
    return redirect(url_for("home"))

@app.route("/add_vehicle", methods=["GET", "POST"])
@login_required
def add_vehicle() -> str:
    if request.method == "POST":
        name = request.form["name"]
        vtype = request.form["type"]
        registration = request.form["registration"]
        new_vehicle = Vehicle(name=name, type=vtype, registration=registration)
        db.session.add(new_vehicle)
        db.session.commit()
        flash("Vehicle added successfully!", "success")
        return redirect(url_for("vehicles"))
    return render_template("add_vehicle.html")

@app.route("/book/<int:vehicle_id>")
@login_required
def book(vehicle_id: int) -> str:
    vehicle = Vehicle.query.get(vehicle_id)
    if vehicle and vehicle.available:
        vehicle.available = False  # Mark vehicle as unavailable after booking
        new_booking = Booking(user_id=session["user_id"], vehicle_id=vehicle.id)
        db.session.add(new_booking)
        db.session.commit()
        flash("Vehicle booked successfully!", "success")
    else:
        flash("Vehicle is not available.", "error")
    return redirect(url_for("home"))

@app.route("/my_bookings")
@login_required
def my_bookings() -> str:
    bookings = Booking.query.filter_by(user_id=session["user_id"]).all()
    return render_template("my_bookings.html", bookings=bookings)

@app.route("/vehicles")
def vehicles() -> str:
    vehicles = Vehicle.query.all()
    return render_template("vehicles.html", vehicles=vehicles)

# Manual Database Initialization
if __name__ == "__main__":
    # Create all tables before starting the app
    with app.app_context():
        db.create_all()

    app.run(debug=True)