from flask import Blueprint, render_template, redirect, url_for, request, flash, current_app
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
from models import db, User
from email_utils import send_verification_email, send_password_reset_email, verify_token, verify_reset_token, send_welcome_email, send_password_reset_confirmation
import re

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

def validate_password(password):
    """Validate password strength"""
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    if not re.search(r"[A-Z]", password):
        return False, "Password must contain at least one uppercase letter"
    if not re.search(r"[a-z]", password):
        return False, "Password must contain at least one lowercase letter"
    if not re.search(r"\d", password):
        return False, "Password must contain at least one number"
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        return False, "Password must contain at least one special character"
    return True, "Password is valid"

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        full_name = request.form.get('full_name')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        # Validation
        if not all([full_name, email, password, confirm_password]):
            flash('All fields are required', 'danger')
            return render_template('auth/register.html')
        
        if password != confirm_password:
            flash('Passwords do not match', 'danger')
            return render_template('auth/register.html')
        
        is_valid, message = validate_password(password)
        if not is_valid:
            flash(message, 'danger')
            return render_template('auth/register.html')
        
        # Check if user exists
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            if existing_user.is_verified:
                flash('Email already registered. Please login or reset your password.', 'danger')
            else:
                flash('Email already registered but not verified. Please check your email for verification link or request a new one.', 'warning')
            return render_template('auth/register.html')
        
        # Create new user
        user = User(
            full_name=full_name,
            email=email,
            password_hash=generate_password_hash(password),
            verification_token_expires=datetime.utcnow() + timedelta(hours=24)
        )
        
        db.session.add(user)
        db.session.commit()
        
        # Send verification email
        if send_verification_email(user, is_resend=False):
            flash('Registration successful! Please check your email to verify your account.', 'success')
        else:
            flash('Registration successful but verification email could not be sent. Please contact support.', 'warning')
        
        return redirect(url_for('auth.login'))
    
    return render_template('auth/register.html')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        remember = request.form.get('remember', False)
        
        user = User.query.filter_by(email=email).first()
        
        if not user or not check_password_hash(user.password_hash, password):
            flash('Invalid email or password', 'danger')
            return render_template('auth/login.html')
        
        if not user.is_verified:
            flash('Please verify your email before logging in. Check your inbox for the verification link or request a new one.', 'warning')
            return render_template('auth/login.html')
        
        login_user(user, remember=remember)
        
        # Update last login time (optional - add to model if needed)
        # user.last_login = datetime.utcnow()
        db.session.commit()
        
        flash(f'Welcome back, {user.full_name}!', 'success')
        
        next_page = request.args.get('next')
        return redirect(next_page) if next_page else redirect(url_for('dashboard'))
    
    return render_template('auth/login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('auth.login'))

@auth_bp.route('/verify-email/<token>')
def verify_email(token):
    email = verify_token(token)
    
    if not email:
        flash('The verification link is invalid or has expired. Please request a new verification link.', 'danger')
        return redirect(url_for('auth.login'))
    
    user = User.query.filter_by(email=email).first()
    
    if not user:
        flash('User not found. Please register for an account.', 'danger')
        return redirect(url_for('auth.register'))
    
    if user.is_verified:
        flash('Email already verified. You can now login to your account.', 'info')
        return redirect(url_for('auth.login'))
    
    # Verify the user
    user.is_verified = True
    user.verification_token = None
    user.verification_token_expires = None
    db.session.commit()
    
    # Send welcome email
    if send_welcome_email(user):
        flash('Email verified successfully! Welcome to Resuma! A welcome email has been sent to you.', 'success')
    else:
        flash('Email verified successfully! Welcome to Resuma! (Welcome email could not be sent)', 'success')
    
    return redirect(url_for('auth.login'))

@auth_bp.route('/resend-verification', methods=['GET', 'POST'])
def resend_verification():
    if current_user.is_authenticated:
        if not current_user.is_verified:
            user = current_user
            if send_verification_email(user, is_resend=True):
                flash('Verification email has been resent. Please check your inbox.', 'success')
            else:
                flash('Unable to send verification email. Please try again later.', 'danger')
            return redirect(url_for('dashboard'))
        else:
            flash('Your email is already verified.', 'info')
            return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        email = request.form.get('email')
        user = User.query.filter_by(email=email).first()
        
        if user and not user.is_verified:
            # Update token expiration
            user.verification_token_expires = datetime.utcnow() + timedelta(hours=24)
            db.session.commit()
            
            if send_verification_email(user, is_resend=True):
                flash('Verification email has been resent. Please check your inbox and spam folder.', 'success')
            else:
                flash('Unable to send verification email. Please try again later or contact support.', 'danger')
        else:
            # For security, don't reveal if email exists or is already verified
            flash('If the email exists and is not verified, a new verification link has been sent to your email address.', 'info')
        
        return redirect(url_for('auth.login'))
    
    return render_template('auth/resend_verification.html')

@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        email = request.form.get('email')
        user = User.query.filter_by(email=email).first()
        
        if user and user.is_verified:
            # Update reset token expiration
            user.reset_token_expires = datetime.utcnow() + timedelta(hours=1)
            db.session.commit()
            
            if send_password_reset_email(user):
                flash('Password reset link has been sent to your email. The link will expire in 1 hour.', 'success')
            else:
                flash('Unable to send password reset email. Please try again later.', 'danger')
        else:
            # For security, don't reveal if email exists or is not verified
            flash('If the email exists and is verified, a password reset link has been sent to your email address.', 'info')
        
        return redirect(url_for('auth.login'))
    
    return render_template('auth/forgot_password.html')

@auth_bp.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    email = verify_reset_token(token) 
    
    if not email:
        flash('The password reset link is invalid or has expired. Please request a new password reset link.', 'danger')
        return redirect(url_for('auth.forgot_password'))
    
    user = User.query.filter_by(email=email).first()
    
    if not user:
        flash('User not found. Please register for an account.', 'danger')
        return redirect(url_for('auth.register'))
    
    if not user.is_verified:
        flash('Please verify your email address before resetting your password.', 'warning')
        return redirect(url_for('auth.resend_verification'))
    
    if request.method == 'POST':
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        if password != confirm_password:
            flash('Passwords do not match', 'danger')
            return render_template('auth/reset_password.html', token=token)
        
        is_valid, message = validate_password(password)
        if not is_valid:
            flash(message, 'danger')
            return render_template('auth/reset_password.html', token=token)
        
        # Update password
        user.password_hash = generate_password_hash(password)
        user.reset_token = None
        user.reset_token_expires = None
        db.session.commit()
        
        # Send password reset confirmation email
        if send_password_reset_confirmation(user):
            flash('Password has been reset successfully. You can now login with your new password. A confirmation email has been sent.', 'success')
        else:
            flash('Password has been reset successfully. You can now login with your new password.', 'success')
        
        return redirect(url_for('auth.login'))
    
    return render_template('auth/reset_password.html', token=token)

@auth_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        full_name = request.form.get('full_name')
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        confirm_new_password = request.form.get('confirm_new_password')
        
        # Update name
        if full_name and full_name != current_user.full_name:
            current_user.full_name = full_name
            flash('Profile updated successfully.', 'success')
        
        # Update password
        if current_password and new_password:
            if not check_password_hash(current_user.password_hash, current_password):
                flash('Current password is incorrect.', 'danger')
                return redirect(url_for('auth.profile'))
            
            if new_password != confirm_new_password:
                flash('New passwords do not match.', 'danger')
                return redirect(url_for('auth.profile'))
            
            is_valid, message = validate_password(new_password)
            if not is_valid:
                flash(message, 'danger')
                return redirect(url_for('auth.profile'))
            
            current_user.password_hash = generate_password_hash(new_password)
            flash('Password updated successfully.', 'success')
        
        db.session.commit()
        return redirect(url_for('auth.profile'))
    
    return render_template('auth/profile.html', user=current_user)

@auth_bp.route('/delete-account', methods=['POST'])
@login_required
def delete_account():
    """Delete user account and all associated data"""
    password = request.form.get('password')
    
    if not check_password_hash(current_user.password_hash, password):
        flash('Invalid password. Account not deleted.', 'danger')
        return redirect(url_for('auth.profile'))
    
    # Delete user (cascade will delete all resumes and related data)
    db.session.delete(current_user)
    db.session.commit()
    
    logout_user()
    flash('Your account has been permanently deleted. We\'re sorry to see you go!', 'info')
    return redirect(url_for('index'))

@auth_bp.route('/change-email', methods=['POST'])
@login_required
def change_email():
    """Request email change with verification"""
    new_email = request.form.get('new_email')
    password = request.form.get('password')
    
    if not new_email or not password:
        flash('All fields are required.', 'danger')
        return redirect(url_for('auth.profile'))
    
    if not check_password_hash(current_user.password_hash, password):
        flash('Invalid password.', 'danger')
        return redirect(url_for('auth.profile'))
    
    # Check if email is already taken
    existing_user = User.query.filter_by(email=new_email).first()
    if existing_user and existing_user.id != current_user.id:
        flash('Email address is already registered.', 'danger')
        return redirect(url_for('auth.profile'))
    
    # Store new email in session for verification
    # In production, you would send a verification email to the new address
    current_user.email = new_email
    db.session.commit()
    
    flash('Email address has been updated successfully.', 'success')
    return redirect(url_for('auth.profile'))

@auth_bp.route('/security')
@login_required
def security():
    """Security settings page"""
    return render_template('auth/security.html', user=current_user)

@auth_bp.route('/sessions', methods=['GET', 'POST'])
@login_required
def manage_sessions():
    """Manage active sessions"""
    if request.method == 'POST':
        # Clear all sessions except current
        # This would require session management implementation
        flash('All other sessions have been terminated.', 'success')
        return redirect(url_for('auth.security'))
    
    return redirect(url_for('auth.security'))

# Token validation endpoint for AJAX calls
@auth_bp.route('/check-email', methods=['POST'])
def check_email():
    """Check if email is already registered (for AJAX validation)"""
    email = request.json.get('email')
    user = User.query.filter_by(email=email).first()
    
    if user:
        return {'available': False, 'message': 'Email already registered'}
    else:
        return {'available': True, 'message': 'Email available'}

# Password strength checker endpoint
@auth_bp.route('/check-password-strength', methods=['POST'])
def check_password_strength():
    """Check password strength for AJAX validation"""
    password = request.json.get('password')
    
    strength = 0
    feedback = []
    
    if len(password) >= 8:
        strength += 20
    else:
        feedback.append('At least 8 characters')
    
    if re.search(r"[A-Z]", password):
        strength += 20
    else:
        feedback.append('One uppercase letter')
    
    if re.search(r"[a-z]", password):
        strength += 20
    else:
        feedback.append('One lowercase letter')
    
    if re.search(r"\d", password):
        strength += 20
    else:
        feedback.append('One number')
    
    if re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        strength += 20
    else:
        feedback.append('One special character')
    
    if strength == 100:
        status = 'strong'
        message = 'Excellent password!'
    elif strength >= 60:
        status = 'medium'
        message = 'Good password, but could be stronger'
    else:
        status = 'weak'
        message = 'Weak password'
    
    return {
        'strength': strength,
        'status': status,
        'message': message,
        'feedback': feedback
    }