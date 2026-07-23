from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, current_user, login_required
from app.models import db, User
import re

auth_bp = Blueprint('auth', __name__)


def password_requirements_errors(password: str) -> list:
    """Returns a list of unmet password requirements (empty list = strong enough)."""
    errors = []
    if len(password) < 8:
        errors.append("at least 8 characters")
    if not re.search(r"[A-Z]", password):
        errors.append("one uppercase letter")
    if not re.search(r"[a-z]", password):
        errors.append("one lowercase letter")
    if not re.search(r"[0-9]", password):
        errors.append("one number")
    if not re.search(r"[^A-Za-z0-9]", password):
        errors.append("one special character (e.g. !@#$%)")
    return errors

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
        
    if request.method == 'POST':
        login_id = request.form.get('login_id', '').strip()
        password = request.form.get('password')
        
        # Allow login with either email or username
        if '@' in login_id:
            user = User.query.filter_by(email=login_id).first()
        else:
            user = User.query.filter_by(username=login_id).first()
        
        if user is None or not user.check_password(password):
            return render_template('login.html', error="Invalid credentials. Please check your email/username and password.")
            
        login_user(user)
        next_page = request.args.get('next')
        if not next_page or not next_page.startswith('/'):
            next_page = url_for('home')
        return redirect(next_page)
        
    return render_template('login.html')

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
        
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        if not username or not email or not password:
            return render_template('register.html', error="All fields are required")
        
        if '@' not in email or '.' not in email:
            return render_template('register.html', error="Please enter a valid email address")
            
        if password != confirm_password:
            return render_template('register.html', error="Passwords do not match")

        weak_points = password_requirements_errors(password)
        if weak_points:
            return render_template(
                'register.html',
                error="Password must have " + ", ".join(weak_points) + "."
            )
            
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            return render_template('register.html', error="Username already exists")
        
        existing_email = User.query.filter_by(email=email).first()
        if existing_email:
            return render_template('register.html', error="Email is already registered")
            
        user = User(username=username, email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        
        login_user(user)
        return redirect(url_for('home'))
        
    return render_template('register.html')

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))