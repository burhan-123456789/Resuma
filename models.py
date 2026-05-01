from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime
import json

db = SQLAlchemy()

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    full_name = db.Column(db.String(100), nullable=False)
    is_verified = db.Column(db.Boolean, default=False)
    verification_token = db.Column(db.String(255), nullable=True)
    verification_token_expires = db.Column(db.DateTime, nullable=True)
    reset_token = db.Column(db.String(255), nullable=True)
    reset_token_expires = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    resumes = db.relationship('Resume', backref='author', lazy=True, cascade='all, delete-orphan')
    
    def get_id(self):
        return str(self.id)

class Resume(db.Model):
    __tablename__ = 'resumes'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    title = db.Column(db.String(100), nullable=False, default='Untitled Resume')
    selected_theme = db.Column(db.String(50), nullable=False, default='modern_1')
    theme_category = db.Column(db.String(20), nullable=False, default='designed')
    theme_settings = db.Column(db.Text, default='{}')
    pdf_name = db.Column(db.String(200), nullable=True)
    pdf_generation_method = db.Column(db.String(20), default='auto')  # auto, weasyprint, xhtml2pdf, reportlab
    share_token = db.Column(db.String(100), unique=True, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    personal_info = db.relationship('PersonalInfo', backref='resume', uselist=False, cascade='all, delete-orphan')
    summaries = db.relationship('Summary', backref='resume', lazy=True, cascade='all, delete-orphan')
    education = db.relationship('Education', backref='resume', lazy=True, cascade='all, delete-orphan')
    experiences = db.relationship('Experience', backref='resume', lazy=True, cascade='all, delete-orphan')
    skills = db.relationship('Skill', backref='resume', lazy=True, cascade='all, delete-orphan')
    projects = db.relationship('Project', backref='resume', lazy=True, cascade='all, delete-orphan')
    certifications = db.relationship('Certification', backref='resume', lazy=True, cascade='all, delete-orphan')
    languages = db.relationship('Language', backref='resume', lazy=True, cascade='all, delete-orphan')
    social_links = db.relationship('SocialLink', backref='resume', lazy=True, cascade='all, delete-orphan')
    
    def get_theme_settings(self):
        return json.loads(self.theme_settings) if self.theme_settings else {}
    
    def set_theme_settings(self, settings):
        self.theme_settings = json.dumps(settings)

class PersonalInfo(db.Model):
    __tablename__ = 'personal_info'
    
    id = db.Column(db.Integer, primary_key=True)
    resume_id = db.Column(db.Integer, db.ForeignKey('resumes.id'), nullable=False, unique=True)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    address = db.Column(db.String(200), nullable=True)
    city = db.Column(db.String(50), nullable=True)
    country = db.Column(db.String(50), nullable=True)
    postal_code = db.Column(db.String(20), nullable=True)
    job_title = db.Column(db.String(100), nullable=True)
    
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

class Summary(db.Model):
    __tablename__ = 'summaries'
    
    id = db.Column(db.Integer, primary_key=True)
    resume_id = db.Column(db.Integer, db.ForeignKey('resumes.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    order = db.Column(db.Integer, default=0)

class Education(db.Model):
    __tablename__ = 'education'
    
    id = db.Column(db.Integer, primary_key=True)
    resume_id = db.Column(db.Integer, db.ForeignKey('resumes.id'), nullable=False)
    institution = db.Column(db.String(200), nullable=False)
    degree = db.Column(db.String(100), nullable=False)
    field_of_study = db.Column(db.String(100), nullable=True)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=True)
    current = db.Column(db.Boolean, default=False)
    description = db.Column(db.Text, nullable=True)
    order = db.Column(db.Integer, default=0)

class Experience(db.Model):
    __tablename__ = 'experiences'
    
    id = db.Column(db.Integer, primary_key=True)
    resume_id = db.Column(db.Integer, db.ForeignKey('resumes.id'), nullable=False)
    company = db.Column(db.String(200), nullable=False)
    position = db.Column(db.String(100), nullable=False)
    location = db.Column(db.String(100), nullable=True)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=True)
    current = db.Column(db.Boolean, default=False)
    description = db.Column(db.Text, nullable=True)
    order = db.Column(db.Integer, default=0)

class Skill(db.Model):
    __tablename__ = 'skills'
    
    id = db.Column(db.Integer, primary_key=True)
    resume_id = db.Column(db.Integer, db.ForeignKey('resumes.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(50), nullable=True)
    level = db.Column(db.String(20), nullable=True)  # Beginner, Intermediate, Advanced, Expert
    order = db.Column(db.Integer, default=0)

class Project(db.Model):
    __tablename__ = 'projects'
    
    id = db.Column(db.Integer, primary_key=True)
    resume_id = db.Column(db.Integer, db.ForeignKey('resumes.id'), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    technologies = db.Column(db.String(500), nullable=True)
    link = db.Column(db.String(200), nullable=True)
    start_date = db.Column(db.Date, nullable=True)
    end_date = db.Column(db.Date, nullable=True)
    order = db.Column(db.Integer, default=0)

class Certification(db.Model):
    __tablename__ = 'certifications'
    
    id = db.Column(db.Integer, primary_key=True)
    resume_id = db.Column(db.Integer, db.ForeignKey('resumes.id'), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    issuer = db.Column(db.String(200), nullable=False)
    issue_date = db.Column(db.Date, nullable=True)
    expiry_date = db.Column(db.Date, nullable=True)
    credential_id = db.Column(db.String(100), nullable=True)
    link = db.Column(db.String(200), nullable=True)
    order = db.Column(db.Integer, default=0)

class Language(db.Model):
    __tablename__ = 'languages'
    
    id = db.Column(db.Integer, primary_key=True)
    resume_id = db.Column(db.Integer, db.ForeignKey('resumes.id'), nullable=False)
    name = db.Column(db.String(50), nullable=False)
    proficiency = db.Column(db.String(20), nullable=False)  # Basic, Conversational, Professional, Native
    order = db.Column(db.Integer, default=0)

class SocialLink(db.Model):
    __tablename__ = 'social_links'
    
    id = db.Column(db.Integer, primary_key=True)
    resume_id = db.Column(db.Integer, db.ForeignKey('resumes.id'), nullable=False)
    platform = db.Column(db.String(50), nullable=False)  # LinkedIn, GitHub, Twitter, etc.
    url = db.Column(db.String(200), nullable=False)
    order = db.Column(db.Integer, default=0)