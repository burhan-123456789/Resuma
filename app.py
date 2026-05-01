from flask import Flask, render_template, request, session, jsonify, redirect, url_for, flash
from flask_login import LoginManager, current_user
from models import db, User
from email_utils import init_email
from config import Config
from datetime import datetime, timedelta, timezone
from flask_migrate import Migrate
from models import db
import os
import logging
from logging.handlers import RotatingFileHandler
import atexit
import time

# Import blueprints and routes
from auth import auth_bp
from routes import init_routes

def create_app(config_class=Config):
    """Application factory pattern"""
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # Ensure instance folder exists
    os.makedirs(app.instance_path, exist_ok=True)
    
    # Setup logging
    setup_logging(app)
    
    # Initialize extensions
    db.init_app(app)
    init_email(app)
    
    migrate = Migrate(app, db)
    
    # Initialize login manager
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'info'
    login_manager.session_protection = 'strong'
    
    @login_manager.user_loader
    def load_user(user_id):
        """Load user by ID for Flask-Login"""
        try:
            # Use Session.get() instead of Query.get() for SQLAlchemy 2.0 compatibility
            return db.session.get(User, int(user_id))
        except:
            return None
    
    @login_manager.unauthorized_handler
    def unauthorized():
        """Handle unauthorized access"""
        flash('You need to be logged in to access this page.', 'warning')
        return redirect(url_for('auth.login'))
    
    # Register blueprints
    app.register_blueprint(auth_bp)
    
    # Initialize routes (this will register all other routes)
    init_routes(app)
    
    # Create database tables
    with app.app_context():
        db.create_all()
        app.logger.info("Database tables created successfully")
    
    # Register custom template filters
    register_template_filters(app)
    
    # Register error handlers
    register_error_handlers(app)
    
    # Register context processors
    register_context_processors(app)
    
    # Register before request handlers
    register_before_request_handlers(app)
    
    return app

def setup_logging(app):
    """Setup application logging with Windows compatibility"""
    # Remove default handlers
    for handler in app.logger.handlers[:]:
        app.logger.removeHandler(handler)
    
    # Set log level
    log_level = logging.DEBUG if app.debug else logging.INFO
    app.logger.setLevel(log_level)
    
    # Always add console handler (for development)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_format = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    console_handler.setFormatter(console_format)
    app.logger.addHandler(console_handler)
    
    # Only add file handler if not in debug mode or if logs directory exists
    if not app.debug:
        try:
            # Create logs directory if it doesn't exist
            logs_dir = 'logs'
            if not os.path.exists(logs_dir):
                os.makedirs(logs_dir, exist_ok=True)
            
            log_file = os.path.join(logs_dir, 'resuma.log')
            
            # Close any existing handlers to release file locks
            for handler in app.logger.handlers:
                if isinstance(handler, RotatingFileHandler):
                    try:
                        handler.close()
                        app.logger.removeHandler(handler)
                    except:
                        pass
            
            # Create new file handler with delay=True to prevent immediate file locking
            file_handler = RotatingFileHandler(
                log_file,
                maxBytes=10485760,  # 10MB
                backupCount=5,
                delay=True  # Important: Don't open the file immediately
            )
            file_handler.setLevel(logging.INFO)
            file_format = logging.Formatter(
                '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
            )
            file_handler.setFormatter(file_format)
            app.logger.addHandler(file_handler)
            
            app.logger.info('Resuma application startup')
            
        except Exception as e:
            # If file logging fails, continue with console only
            app.logger.warning(f'Could not set up file logging: {e}')
    else:
        app.logger.info('Resuma application startup (debug mode)')

def get_utc_now():
    """Get current UTC datetime as timezone-aware"""
    return datetime.now(timezone.utc)

def register_template_filters(app):
    """Register custom Jinja2 filters"""
    
    @app.template_filter('time_since')
    def time_since_filter(date):
        """Return time since date"""
        if not date:
            return 'Never'
        
        # Make date timezone-aware if it isn't already
        if date.tzinfo is None:
            date = date.replace(tzinfo=timezone.utc)
        
        now = get_utc_now()
        diff = now - date
        
        seconds = diff.total_seconds()
        
        if seconds < 60:
            return 'Just now'
        elif seconds < 3600:
            minutes = int(seconds / 60)
            return f'{minutes} minute{"s" if minutes != 1 else ""} ago'
        elif seconds < 86400:
            hours = int(seconds / 3600)
            return f'{hours} hour{"s" if hours != 1 else ""} ago'
        elif seconds < 604800:
            days = int(seconds / 86400)
            return f'{days} day{"s" if days != 1 else ""} ago'
        elif seconds < 2592000:
            weeks = int(seconds / 604800)
            return f'{weeks} week{"s" if weeks != 1 else ""} ago'
        else:
            return date.strftime('%B %d, %Y')
    
    @app.template_filter('format_date')
    def format_date_filter(date, format='%B %d, %Y'):
        """Format date with custom format"""
        if not date:
            return ''
        return date.strftime(format)
    
    @app.template_filter('truncate')
    def truncate_filter(text, length=100, suffix='...'):
        """Truncate text to specified length"""
        if not text:
            return ''
        if len(text) <= length:
            return text
        return text[:length].rsplit(' ', 1)[0] + suffix
    
    @app.template_filter('nl2br')
    def nl2br_filter(text):
        """Convert newlines to HTML line breaks"""
        if not text:
            return ''
        return text.replace('\n', '<br>')
    
    @app.template_filter('default_theme')
    def default_theme_filter(value, default='modern_1'):
        """Return default if value is None or empty"""
        return value if value else default

def register_error_handlers(app):
    """Register custom error handlers"""
    
    @app.errorhandler(400)
    def bad_request_error(error):
        """Handle 400 Bad Request errors"""
        app.logger.error(f'Bad Request: {error}')
        if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'error': 'Bad request', 'message': str(error)}), 400
        flash('Bad request. Please check your input and try again.', 'danger')
        return render_template('errors/400.html'), 400
    
    @app.errorhandler(403)
    def forbidden_error(error):
        """Handle 403 Forbidden errors"""
        app.logger.error(f'Forbidden access: {error}')
        if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'error': 'Forbidden', 'message': 'You do not have permission to access this resource'}), 403
        flash('You do not have permission to access this page.', 'danger')
        return render_template('errors/403.html'), 403
    
    @app.errorhandler(404)
    def not_found_error(error):
        """Handle 404 Not Found errors"""
        app.logger.error(f'Page not found: {error}')
        if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'error': 'Not found', 'message': 'The requested resource was not found'}), 404
        return render_template('errors/404.html'), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        """Handle 500 Internal Server errors"""
        app.logger.error(f'Server Error: {error}')
        db.session.rollback()
        if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'error': 'Server error', 'message': 'An internal server error occurred'}), 500
        flash('An internal server error occurred. Please try again later.', 'danger')
        return render_template('errors/500.html'), 500
    
    @app.errorhandler(413)
    def too_large_error(error):
        """Handle 413 Request Entity Too Large errors"""
        app.logger.error(f'File too large: {error}')
        flash('The file you uploaded is too large.', 'danger')
        return redirect(request.url), 413
    
    @app.errorhandler(429)
    def too_many_requests_error(error):
        """Handle 429 Too Many Requests errors"""
        app.logger.warning(f'Rate limit exceeded: {error}')
        flash('Too many requests. Please try again later.', 'warning')
        return render_template('errors/429.html'), 429

def register_context_processors(app):
    """Register context processors for templates"""
    
    @app.context_processor
    def utility_processor():
        """Add utility functions to all templates"""
        def get_year():
            return get_utc_now().year
        
        def is_active_page(endpoint):
            """Check if current page matches endpoint"""
            return request.endpoint == endpoint
        
        def get_user_resume_count():
            """Get count of user's resumes"""
            if current_user.is_authenticated:
                return current_user.resumes.count()
            return 0
        
        return {
            'now': get_utc_now(),
            'year': get_year(),
            'is_active_page': is_active_page,
            'user_resume_count': get_user_resume_count,
            'app_name': app.config.get('APP_NAME', 'Resuma'),
            'app_version': '1.0.0'
        }
    
    @app.context_processor
    def theme_processor():
        """Add theme-related utilities"""
        def get_theme_categories():
            return {
                'designed': ['modern_1', 'modern_2', 'modern_3', 'modern_4', 'modern_5', 
                            'modern_6', 'modern_7', 'modern_8', 'modern_9', 'modern_10'],
                'ats': ['ats_1', 'ats_2', 'ats_3', 'ats_4', 'ats_5', 
                       'ats_6', 'ats_7', 'ats_8', 'ats_9', 'ats_10']
            }
        
        return {
            'theme_categories': get_theme_categories
        }

def register_before_request_handlers(app):
    """Register before request handlers"""
    
    @app.before_request
    def before_request():
        """Execute before each request"""
        # Set session permanent
        session.permanent = True
        
        # Update last seen for authenticated users
        if current_user.is_authenticated:
            # This would require adding last_seen column to User model
            # current_user.last_seen = get_utc_now()
            # db.session.commit()
            pass
        
        # Log API requests (only in debug mode to reduce file I/O)
        if app.debug and request.path.startswith('/api/'):
            app.logger.debug(f'API Request: {request.method} {request.path}')
    
    @app.after_request
    def after_request(response):
        """Execute after each request"""
        # Add security headers
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        
        # Only add HSTS in production
        if not app.debug:
            response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        
        # Prevent caching for authenticated pages
        if current_user.is_authenticated:
            response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
            response.headers['Pragma'] = 'no-cache'
            response.headers['Expires'] = '-1'
        
        return response

# Create upload and logs directories
def ensure_directories():
    """Ensure required directories exist"""
    directories = [
        'logs',
        'instance',
        'static/uploads',
        'static/temp'
    ]
    
    for directory in directories:
        try:
            os.makedirs(directory, exist_ok=True)
        except Exception as e:
            print(f"Warning: Could not create directory {directory}: {e}")

# Clean up old log files
def cleanup_old_logs():
    """Clean up old log files to prevent accumulation"""
    logs_dir = 'logs'
    if os.path.exists(logs_dir):
        try:
            for filename in os.listdir(logs_dir):
                if filename.startswith('resuma.log') and filename != 'resuma.log':
                    filepath = os.path.join(logs_dir, filename)
                    # Delete files older than 7 days
                    if os.path.getmtime(filepath) < time.time() - 7 * 86400:
                        os.remove(filepath)
        except Exception as e:
            print(f"Warning: Could not clean up old logs: {e}")

# Main entry point
if __name__ == '__main__':
    # Create necessary directories
    ensure_directories()
    
    # Clean up old logs
    cleanup_old_logs()
    
    # Create app
    app = create_app()
    
    # Get host and port from environment or use defaults
    host = os.environ.get('HOST', '0.0.0.0')
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV', 'production') == 'development'
    
    # Start application
    print(f'Starting Resuma application on {host}:{port} (debug={debug})')
    
    # Run app
    app.run(
        host=host,
        port=port,
        debug=debug,
        threaded=True,
        use_reloader=False
    )