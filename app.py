import os
import re
from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from datetime import datetime

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'super_secret_key')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///vehicle_rental.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
migrate = Migrate(app, db)

# Database Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    bookings = db.relationship('Booking', backref='user', lazy=True)
    reviews = db.relationship('Review', backref='user', lazy=True)

class Vehicle(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    type = db.Column(db.String(100), nullable=False)
    registration = db.Column(db.String(100), unique=True, nullable=False)
    rent = db.Column(db.Integer, nullable=False, default=0)
    available = db.Column(db.Boolean, default=True)
    bookings = db.relationship('Booking', backref='vehicle', lazy=True)
    reviews = db.relationship('Review', backref='vehicle', lazy=True)

class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    vehicle_id = db.Column(db.Integer, db.ForeignKey('vehicle.id'), nullable=False)
    payment_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    amount_paid = db.Column(db.Float, nullable=False)

class Review(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    vehicle_id = db.Column(db.Integer, db.ForeignKey('vehicle.id'), nullable=False)
    rating = db.Column(db.Integer, nullable=False)
    comment = db.Column(db.Text, nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

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
def home():
    return render_template("home.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            error = "Username already exists!"
            return render_template("register.html", error=error)

        # Check password complexity
        password_regex = r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$'
        if not re.match(password_regex, password):
            error = "Password must be at least 8 characters long, and include uppercase and lowercase letters, a number, and a symbol."
            return render_template("register.html", error=error)

        hashed_password = generate_password_hash(password, method="pbkdf2:sha256")
        new_user = User(username=username, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()

        flash("Registration successful! Please log in.", "success")
        return redirect(url_for("login"))

    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            session["user_id"] = user.id
            flash("Login successful!", "success")
            return redirect(url_for("home"))
        else:
            flash("Invalid credentials!", "error")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.pop("user_id", None)
    flash("Logged out successfully!", "info")
    return redirect(url_for("home"))

@app.route("/add_vehicle", methods=["GET", "POST"])
@login_required
def add_vehicle():
    if request.method == "POST":
        name = request.form["name"]
        vtype = request.form["type"]
        registration = request.form["registration"]
        rent = request.form["rent"]

        if not name or not vtype or not registration or not rent:
            flash("All fields are required!", "error")
            return redirect(url_for("add_vehicle"))

        existing_vehicle = Vehicle.query.filter_by(registration=registration).first()
        if existing_vehicle:
            flash("Registration number already exists!", "error")
            return redirect(url_for("add_vehicle"))

        new_vehicle = Vehicle(name=name, type=vtype, registration=registration, rent=rent)
        db.session.add(new_vehicle)
        db.session.commit()
        flash("Vehicle added successfully!", "success")
        return redirect(url_for("vehicles"))

    return render_template("add_vehicle.html")

@app.route("/update_vehicle/<int:vehicle_id>", methods=["GET", "POST"])
@login_required
def update_vehicle(vehicle_id):
    vehicle = Vehicle.query.get_or_404(vehicle_id)
    if request.method == "POST":
        vehicle.name = request.form["name"]
        vehicle.type = request.form["type"]
        vehicle.registration = request.form["registration"]
        vehicle.rent = request.form["rent"]
        vehicle.available = 'available' in request.form
        db.session.commit()
        flash("Vehicle updated successfully!", "success")
        return redirect(url_for("vehicles"))
    return render_template("update_vehicle.html", vehicle=vehicle)

@app.route("/delete_vehicle/<int:vehicle_id>", methods=["POST"])
@login_required
def delete_vehicle(vehicle_id):
    vehicle = Vehicle.query.get_or_404(vehicle_id)
    
    # Delete associated bookings
    Booking.query.filter_by(vehicle_id=vehicle_id).delete()
    
    db.session.delete(vehicle)
    db.session.commit()
    flash("Vehicle and associated bookings deleted successfully!", "success")
    return redirect(url_for("vehicles"))

@app.route("/book/<int:vehicle_id>")
@login_required
def book(vehicle_id):
    vehicle = Vehicle.query.get(vehicle_id)
    if vehicle and vehicle.available:
        # Redirect to the payment page
        return redirect(url_for("payment", vehicle_id=vehicle_id))
    else:
        flash("Vehicle is not available.", "error")
        return redirect(url_for("home"))

@app.route("/payment/<int:vehicle_id>", methods=["GET", "POST"])
@login_required
def payment(vehicle_id):
    vehicle = Vehicle.query.get_or_404(vehicle_id)
    if request.method == "POST":
        # Simulate payment processing and booking the vehicle
        amount_paid = vehicle.rent  # Assuming the rent amount is the payment amount
        payment_date = datetime.utcnow()

        if vehicle and vehicle.available:
            vehicle.available = False
            new_booking = Booking(
                user_id=session["user_id"], 
                vehicle_id=vehicle.id, 
                payment_date=payment_date, 
                amount_paid=amount_paid
            )
            db.session.add(new_booking)
            db.session.commit()
            flash("Vehicle booked successfully!", "success")
            return redirect(url_for("my_bookings"))

    return render_template("payment.html", vehicle=vehicle)

@app.route("/my_bookings")
@login_required
def my_bookings():
    bookings = Booking.query.filter_by(user_id=session["user_id"]).all()
    return render_template("my_bookings.html", bookings=bookings)

@app.route("/unbook/<int:booking_id>", methods=["POST"])
@login_required
def unbook(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    if booking.user_id != session["user_id"]:
        flash("You do not have permission to unbook this vehicle.", "error")
        return redirect(url_for("my_bookings"))
    
    vehicle = Vehicle.query.get(booking.vehicle_id)
    if vehicle:
        vehicle.available = True
    
    db.session.delete(booking)
    db.session.commit()
    flash("Booking cancelled successfully!", "success")
    return redirect(url_for("my_bookings"))

@app.route("/vehicles")
def vehicles():
    vehicles = Vehicle.query.all()
    return render_template("vehicles.html", vehicles=vehicles)

@app.route("/search", methods=["GET"])
def search():
    query = request.args.get("query")
    vehicles = Vehicle.query.filter(Vehicle.name.like(f"%{query}%") | Vehicle.type.like(f"%{query}%") | Vehicle.registration.like(f"%{query}%")).all()
    return render_template("search_results.html", vehicles=vehicles)

@app.route("/vehicle/<int:vehicle_id>", methods=["GET"])
def vehicle_details(vehicle_id):
    vehicle = Vehicle.query.get_or_404(vehicle_id)
    return render_template("vehicle_details.html", vehicle=vehicle)

@app.route("/add_review/<int:vehicle_id>", methods=["POST"])
@login_required
def add_review(vehicle_id):
    rating = int(request.form["rating"])
    comment = request.form["comment"]

    new_review = Review(user_id=session["user_id"], vehicle_id=vehicle_id, rating=rating, comment=comment)
    db.session.add(new_review)
    db.session.commit()

    flash("Review added successfully!", "success")
    return redirect(url_for("vehicle_details", vehicle_id=vehicle_id))

if __name__ == "__main__":
    with app.app_context():
        db.create_all()

    app.run(debug=True)