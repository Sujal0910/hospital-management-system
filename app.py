# Import necessary modules from Flask and its extensions
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin, LoginManager, login_user,logout_user,login_required,current_user
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import os

# Get the absolute path of the directory where this file is located
basedir = os.path.abspath(os.path.dirname(__file__))

# Initialize the Flask application
app = Flask(__name__)

# --- Configuration ---
# Set a secret key for session management and security.
app.config['SECRET_KEY'] = 'a-very-secret-key'

# --- START OF THE FIX ---
# Ensure the instance folder exists
instance_path = os.path.join(basedir, 'instance')
os.makedirs(instance_path, exist_ok=True) # This creates the folder if it doesn't exist
# Configure the SQLite database URI.
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(instance_path, 'hospital.db')
# --- END OF THE FIX ---

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize the SQLAlchemy extension with our app
db = SQLAlchemy(app)

# Initialize Flask-Login for handling user sessions
login_manager = LoginManager()
login_manager.init_app(app)
# Tell Flask-Login which view to redirect to when a user needs to log in
login_manager.login_view = 'login'

# --- Database Models ---
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(150), nullable=False)
    role = db.Column(db.String(50), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


class Doctor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    specialization = db.Column(db.String(100), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user = db.relationship('User', backref=db.backref('doctor', uselist=False))

class Patient(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    contact = db.Column(db.String(20), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user = db.relationship('User', backref=db.backref('patient', uselist=False))

class Appointment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patient.id'), nullable=False)
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctor.id'), nullable=False)
    appointment_date = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.String(20), nullable=False, default='Booked')
    reason = db.Column(db.Text, nullable=True)

    patient = db.relationship('Patient', backref='appointments')
    doctor = db.relationship('Doctor', backref='appointments')

class Treatment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    appointment_id = db.Column(db.Integer, db.ForeignKey('appointment.id'), nullable=False)
    diagnosis = db.Column(db.Text, nullable=False)
    prescription = db.Column(db.Text, nullable=False)
    notes = db.Column(db.Text, nullable=True)

    appointment = db.relationship('Appointment', backref=db.backref('treatment', uselist=False))

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            flash("You do not have permission to access this page.", "danger")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function
# --- Main Application Logic ---
@app.route('/')
def index():
    return "<h1>Welcome to the Hospital Management System!</h1>"
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()

        if user and user.check_password(password):
            login_user(user)
            flash('Logged in successfully!', 'success')
            if user.role == 'admin':
                return redirect(url_for('admin_dashboard'))
            # We will add redirects for doctors and patients here later
            else:
                return redirect(url_for('login'))  
        else:
            flash('Invalid email or password.', 'danger')
            
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been LoggedOut ','info')
    return redirect(url_for('login'))



@app.route('/admin/dashboard')
@login_required
@admin_required
def admin_dashboard():
    return render_template('admin_dashboard.html')


@app.route('/admin/add_doctor', methods=['GET', 'POST'])
@login_required
@admin_required
def add_doctor():
    if request.method == 'POST':
        name = request.form.get('name')
        specialization = request.form.get('specialization')
        email = request.form.get('email')
        password = request.form.get('password')

        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash('Email address already in use.', 'danger')
            return redirect(url_for('add_doctor'))

        new_user = User(
            email=email,
            role='doctor'
        )
        new_user.set_password(password)
        db.session.add(new_user)
        
        new_doctor = Doctor(
            name=name,
            specialization=specialization,
            user=new_user
        )
        db.session.add(new_doctor)
        db.session.commit()
        
        flash('Doctor added successfully!', 'success')
        return redirect(url_for('admin_dashboard'))

    return render_template('add_doctor.html')

@app.route('/admin/doctors')
@login_required
@admin_required
def manage_doctors():
    doctors=Doctor.query.all()
    return render_template('manage_doctors.html',doctors=doctors)



@app.route('/admin/edit_doctor/<int:doctor_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_doctor(doctor_id):
    doctor =Doctor.query.get_or_404(doctor_id)
    if request.method == 'POST':
        doctor.name= request.form.get('name')
        doctor.specialization=request.form.get('specialization')
        new_email=request.form.get('email')
        if new_email != doctor.user.email:
            existing_user = User.query.filter_by(email=new_email).first()
            if existing_user:
                flash('That email is already in use by another account.', 'danger')
                return redirect(url_for('edit_doctor', doctor_id=doctor.id))
            doctor.user.email = new_email
        db.session.commit()
        flash('Doctor profile updated successfully!', 'success')
        return redirect(url_for('manage_doctors'))

    return render_template('edit_doctor.html', doctor=doctor)

@app.route('/admin/delete_doctor/<int:doctor_id>', methods=['POST'])
@login_required
@admin_required
def delete_doctor(doctor_id):
    doctor = Doctor.query.get_or_404(doctor_id)
    user = doctor.user

    db.session.delete(doctor)
    db.session.delete(user)
    db.session.commit()

    flash('Doctor has been removed successfully.', 'success')
    return redirect(url_for('manage_doctors'))

























if __name__ == '__main__':
    app.run(debug=True)