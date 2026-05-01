from flask_mail import Mail, Message
from flask import render_template, url_for, current_app
from itsdangerous import URLSafeTimedSerializer
from config import Config
import os
import logging

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

mail = Mail()

def init_email(app):
    """Initialize email with better error handling"""
    try:
        # Test email configuration
        if not app.config.get('MAIL_SERVER'):
            logger.warning("MAIL_SERVER not configured. Email functionality disabled.")
            return
        
        mail.init_app(app)
        
        # Test connection if not in testing mode
        if not app.config.get('TESTING', False):
            with app.app_context():
                # Just check if configuration is valid
                logger.info(f"Email configured with server: {app.config['MAIL_SERVER']}:{app.config['MAIL_PORT']}")
                logger.info(f"Email username: {app.config['MAIL_USERNAME']}")
                
    except Exception as e:
        logger.error(f"Failed to initialize email: {e}")
        logger.warning("Email functionality will be disabled")

def generate_verification_token(email):
    """Generate a verification token for email confirmation"""
    serializer = URLSafeTimedSerializer(Config.SECRET_KEY)
    return serializer.dumps(email, salt='email-verification')

def verify_token(token, expiration=Config.VERIFICATION_TOKEN_EXPIRATION):
    """Verify the email verification token"""
    serializer = URLSafeTimedSerializer(Config.SECRET_KEY)
    try:
        email = serializer.loads(token, salt='email-verification', max_age=expiration)
        return email
    except Exception as e:
        logger.error(f"Token verification failed: {e}")
        return None

def generate_reset_token(email):
    """Generate a password reset token"""
    serializer = URLSafeTimedSerializer(Config.SECRET_KEY)
    return serializer.dumps(email, salt='password-reset')

def verify_reset_token(token, expiration=Config.RESET_TOKEN_EXPIRATION):
    """Verify the password reset token"""
    serializer = URLSafeTimedSerializer(Config.SECRET_KEY)
    try:
        email = serializer.loads(token, salt='password-reset', max_age=expiration)
        return email
    except Exception as e:
        logger.error(f"Reset token verification failed: {e}")
        return None

def send_email(to, subject, template, **kwargs):
    """Generic email sender with error handling"""
    try:
        # Check if email is configured
        if not current_app.config.get('MAIL_SERVER'):
            logger.warning(f"Email not sent to {to}: MAIL_SERVER not configured")
            return False
        
        # For development, print email content
        if current_app.config.get('DEBUG', False) and not current_app.config.get('MAIL_SUPPRESS_SEND', False):
            logger.info(f"Email would be sent to: {to}")
            logger.info(f"Subject: {subject}")
            
            # Still try to send in development if configured
            if not current_app.config.get('MAIL_SUPPRESS_SEND', False):
                msg = Message(subject,
                            sender=current_app.config['MAIL_DEFAULT_SENDER'],
                            recipients=[to])
                msg.html = render_template(template, **kwargs)
                mail.send(msg)
                logger.info(f"Email sent successfully to {to}")
                return True
            else:
                logger.info("Email sending suppressed in development")
                return True
        else:
            # Production - actually send email
            msg = Message(subject,
                        sender=current_app.config['MAIL_DEFAULT_SENDER'],
                        recipients=[to])
            msg.html = render_template(template, **kwargs)
            mail.send(msg)
            logger.info(f"Email sent successfully to {to}")
            return True
            
    except Exception as e:
        logger.error(f"Failed to send email to {to}: {e}")
        
        # Log more details for debugging
        logger.error(f"MAIL_SERVER: {current_app.config.get('MAIL_SERVER')}")
        logger.error(f"MAIL_PORT: {current_app.config.get('MAIL_PORT')}")
        logger.error(f"MAIL_USERNAME: {current_app.config.get('MAIL_USERNAME')}")
        
        return False

def send_verification_email(user, is_resend=False):
    """Send email verification link to user"""
    try:
        token = generate_verification_token(user.email)
        verification_url = url_for('auth.verify_email', token=token, _external=True)
        
        template = 'emails/resend_verification.html' if is_resend else 'emails/verification_email.html'
        
        subject = f'Verify Your Email - {Config.APP_NAME}'
        if is_resend:
            subject = f'Reminder: Verify Your Email - {Config.APP_NAME}'
        
        result = send_email(
            to=user.email,
            subject=subject,
            template=template,
            user=user,
            verification_url=verification_url,
            app_name=Config.APP_NAME,
            app_url=Config.APP_URL
        )
        
        if result:
            logger.info(f"Verification email sent to {user.email}")
        else:
            logger.error(f"Failed to send verification email to {user.email}")
        
        return result
    except Exception as e:
        logger.error(f"Error sending verification email: {e}")
        return False

def send_welcome_email(user):
    """Send welcome email after verification"""
    try:
        result = send_email(
            to=user.email,
            subject=f'Welcome to {Config.APP_NAME}!',
            template='emails/welcome_email.html',
            user=user,
            app_name=Config.APP_NAME,
            app_url=Config.APP_URL
        )
        
        if result:
            logger.info(f"Welcome email sent to {user.email}")
        else:
            logger.error(f"Failed to send welcome email to {user.email}")
        
        return result
    except Exception as e:
        logger.error(f"Error sending welcome email: {e}")
        return False

def send_password_reset_email(user):
    """Send password reset link to user"""
    try:
        token = generate_reset_token(user.email)
        reset_url = url_for('auth.reset_password', token=token, _external=True)
        
        result = send_email(
            to=user.email,
            subject=f'Reset Your Password - {Config.APP_NAME}',
            template='emails/password_reset_email.html',
            user=user,
            reset_url=reset_url,
            app_name=Config.APP_NAME,
            app_url=Config.APP_URL
        )
        
        if result:
            logger.info(f"Password reset email sent to {user.email}")
        else:
            logger.error(f"Failed to send password reset email to {user.email}")
        
        return result
    except Exception as e:
        logger.error(f"Error sending password reset email: {e}")
        return False

def send_password_reset_confirmation(user):
    """Send confirmation email after password reset"""
    try:
        result = send_email(
            to=user.email,
            subject=f'Password Reset Successful - {Config.APP_NAME}',
            template='emails/reset_confirmation.html',
            user=user,
            app_name=Config.APP_NAME,
            app_url=Config.APP_URL
        )
        
        if result:
            logger.info(f"Password reset confirmation sent to {user.email}")
        else:
            logger.error(f"Failed to send password reset confirmation to {user.email}")
        
        return result
    except Exception as e:
        logger.error(f"Error sending password reset confirmation: {e}")
        return False