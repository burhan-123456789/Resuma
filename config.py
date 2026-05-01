import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///resuma.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Email configuration - with proper error handling
    MAIL_SERVER = os.environ.get('MAIL_SERVER')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'True').lower() == 'true'
    MAIL_USE_SSL = os.environ.get('MAIL_USE_SSL', 'False').lower() == 'true'
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER', 'noreply@resuma.com')
    MAIL_DEBUG = os.environ.get('MAIL_DEBUG', 'False').lower() == 'true'
    MAIL_SUPPRESS_SEND = os.environ.get('MAIL_SUPPRESS_SEND', 'False').lower() == 'true'
    
    # Validate email configuration
    @staticmethod
    def validate_email_config():
        """Validate that email configuration is complete"""
        required = ['MAIL_SERVER', 'MAIL_USERNAME', 'MAIL_PASSWORD']
        missing = [req for req in required if not getattr(Config, req)]
        
        if missing:
            print(f"Warning: Missing email configuration: {', '.join(missing)}")
            print("Email functionality will be disabled")
            return False
        return True
    
    # Application settings
    APP_NAME = os.environ.get('APP_NAME', 'Resuma')
    APP_URL = os.environ.get('APP_URL', 'http://localhost:5000')
    
    # Session configuration
    SESSION_TYPE = 'filesystem'
    PERMANENT_SESSION_LIFETIME = 86400  # 24 hours in seconds
    
    # Token expiration times (in seconds)
    VERIFICATION_TOKEN_EXPIRATION = 86400  # 24 hours
    RESET_TOKEN_EXPIRATION = 3600  # 1 hour