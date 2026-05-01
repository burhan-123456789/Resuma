# routes.py - Complete file with all routes

from flask import make_response, render_template, redirect, url_for, request, flash, jsonify, session, abort, send_file
from flask_login import login_required, current_user
from datetime import datetime
import json
import secrets
import traceback
import os
from functools import wraps
from models import db, Resume, PersonalInfo, Summary, Education, Experience, Skill, Project, Certification, Language, SocialLink
from pdf import PDFGenerator, get_resume_data

# Initialize PDF generator
pdf_generator = PDFGenerator()

# Helper function for date formatting in templates
def format_date_for_display(date_value):
    """Format date for display in templates"""
    if date_value is None:
        return None
    if isinstance(date_value, datetime):
        return date_value.strftime('%b %Y')
    if isinstance(date_value, str):
        return date_value
    return str(date_value)

def format_year_for_display(date_value):
    """Format year only for display"""
    if date_value is None:
        return None
    if isinstance(date_value, datetime):
        return date_value.strftime('%Y')
    if isinstance(date_value, str):
        return date_value[:4] if len(date_value) >= 4 else date_value
    return str(date_value)

def no_xframe_options(f):
    """Decorator to allow iframe embedding"""
    @wraps(f)
    def wrapped_function(*args, **kwargs):
        response = f(*args, **kwargs)
        
        # Handle different return types
        if isinstance(response, tuple):
            if len(response) == 2:
                response_obj = make_response(response[0], response[1])
            elif len(response) >= 3:
                response_obj = make_response(response[0], response[1])
                if isinstance(response[2], dict):
                    for key, value in response[2].items():
                        response_obj.headers[key] = value
            else:
                response_obj = make_response(response[0])
        else:
            response_obj = response
            if not hasattr(response_obj, 'headers'):
                response_obj = make_response(response_obj)
        
        # Allow iframe embedding
        if hasattr(response_obj, 'headers'):
            response_obj.headers.pop('X-Frame-Options', None)
            response_obj.headers['X-Frame-Options'] = 'SAMEORIGIN'
        
        return response_obj
    return wrapped_function

def init_routes(app):
    
    @app.after_request
    def add_header_for_pdf(response):
        """Allow iframe embedding for PDF and preview routes"""
        if request.endpoint in ['download_pdf', 'preview_theme', 'preview_template', 'public_resume', 'pdf_preview', 'preview_pdf_content', 'print_view']:
            response.headers['X-Frame-Options'] = 'SAMEORIGIN'
        return response
    
    @app.route('/')
    def index():
        if current_user.is_authenticated:
            return redirect(url_for('dashboard'))
        return render_template('index.html')
    
    @app.route('/dashboard')
    @login_required
    def dashboard():
        resumes = Resume.query.filter_by(user_id=current_user.id).order_by(Resume.updated_at.desc()).all()
        return render_template('dashboard.html', resumes=resumes)
    
    @app.route('/templates')
    @login_required
    def show_templates():
        """Display all available resume templates"""
        return render_template('templates.html')
    
    @app.route('/resume/new', methods=['GET', 'POST'])
    @login_required
    def new_resume():
        if request.method == 'POST':
            title = request.form.get('title', 'Untitled Resume')
            theme = request.form.get('theme', 'modern_1')
            category = request.form.get('category', 'designed')
            
            resume = Resume(
                user_id=current_user.id, 
                title=title,
                selected_theme=theme,
                theme_category=category
            )
            db.session.add(resume)
            db.session.commit()
            flash('Resume created successfully!', 'success')
            return redirect(url_for('edit_resume', resume_id=resume.id))
        
        selected_theme = request.args.get('theme', 'modern_1')
        selected_category = request.args.get('category', 'designed')
        
        return render_template('new_resume.html', 
                             selected_theme=selected_theme, 
                             selected_category=selected_category)
    
    @app.route('/resume/<int:resume_id>/edit', methods=['GET', 'POST'])
    @login_required
    def edit_resume(resume_id):
        resume = Resume.query.get_or_404(resume_id)
        
        if resume.user_id != current_user.id:
            abort(403)
        
        # Check for theme from query params
        theme_from_query = request.args.get('theme')
        category_from_query = request.args.get('category')
        
        if theme_from_query and category_from_query:
            resume.selected_theme = theme_from_query
            resume.theme_category = category_from_query
            db.session.commit()
            flash(f'Theme applied successfully!', 'success')
        
        if request.method == 'POST':
            try:
                data = request.get_json()
                
                if not data:
                    return jsonify({'success': False, 'message': 'No data provided'}), 400
                
                app.logger.info(f"Saving resume {resume_id} data")
                
                # Update title
                if data.get('title'):
                    resume.title = data['title']
                
                # Save personal info
                if data.get('personal_info'):
                    try:
                        if resume.personal_info:
                            for key, value in data['personal_info'].items():
                                if hasattr(resume.personal_info, key) and key not in ['id', 'resume_id', 'created_at', 'updated_at']:
                                    if value is not None:
                                        setattr(resume.personal_info, key, value)
                        else:
                            clean_info = {k: v for k, v in data['personal_info'].items() if v is not None}
                            personal_info = PersonalInfo(resume_id=resume.id, **clean_info)
                            db.session.add(personal_info)
                    except Exception as e:
                        app.logger.error(f"Error saving personal info: {str(e)}")
                
                # Save summaries
                try:
                    if 'summaries' in data:
                        Summary.query.filter_by(resume_id=resume.id).delete()
                        for idx, summary_data in enumerate(data.get('summaries', [])):
                            if summary_data.get('content') and summary_data.get('content').strip():
                                summary = Summary(
                                    resume_id=resume.id,
                                    content=summary_data.get('content', ''),
                                    order=idx
                                )
                                db.session.add(summary)
                except Exception as e:
                    app.logger.error(f"Error saving summaries: {str(e)}")
                
                # Save education
                try:
                    if 'education' in data:
                        Education.query.filter_by(resume_id=resume.id).delete()
                        for idx, edu_data in enumerate(data.get('education', [])):
                            if not edu_data.get('institution') or not edu_data.get('degree'):
                                continue
                                
                            start_date = None
                            end_date = None
                            
                            if edu_data.get('start_date') and edu_data['start_date']:
                                try:
                                    start_date = datetime.strptime(edu_data['start_date'], '%Y-%m-%d')
                                except (ValueError, TypeError):
                                    start_date = None
                            
                            if edu_data.get('end_date') and edu_data['end_date'] and not edu_data.get('current', False):
                                try:
                                    end_date = datetime.strptime(edu_data['end_date'], '%Y-%m-%d')
                                except (ValueError, TypeError):
                                    end_date = None
                            
                            education = Education(
                                resume_id=resume.id,
                                institution=edu_data.get('institution', ''),
                                degree=edu_data.get('degree', ''),
                                field_of_study=edu_data.get('field_of_study', ''),
                                start_date=start_date,
                                end_date=end_date,
                                current=edu_data.get('current', False),
                                description=edu_data.get('description', ''),
                                order=idx
                            )
                            db.session.add(education)
                except Exception as e:
                    app.logger.error(f"Error saving education: {str(e)}")
                    app.logger.error(traceback.format_exc())
                
                # Save experiences
                try:
                    if 'experiences' in data:
                        Experience.query.filter_by(resume_id=resume.id).delete()
                        for idx, exp_data in enumerate(data.get('experiences', [])):
                            if not exp_data.get('company') or not exp_data.get('position'):
                                continue
                                
                            start_date = None
                            end_date = None
                            
                            if exp_data.get('start_date') and exp_data['start_date']:
                                try:
                                    start_date = datetime.strptime(exp_data['start_date'], '%Y-%m-%d')
                                except (ValueError, TypeError):
                                    start_date = None
                            
                            if exp_data.get('end_date') and exp_data['end_date'] and not exp_data.get('current', False):
                                try:
                                    end_date = datetime.strptime(exp_data['end_date'], '%Y-%m-%d')
                                except (ValueError, TypeError):
                                    end_date = None
                            
                            experience = Experience(
                                resume_id=resume.id,
                                company=exp_data.get('company', ''),
                                position=exp_data.get('position', ''),
                                location=exp_data.get('location', ''),
                                start_date=start_date,
                                end_date=end_date,
                                current=exp_data.get('current', False),
                                description=exp_data.get('description', ''),
                                order=idx
                            )
                            db.session.add(experience)
                except Exception as e:
                    app.logger.error(f"Error saving experiences: {str(e)}")
                    app.logger.error(traceback.format_exc())
                
                # Save skills
                try:
                    if 'skills' in data:
                        Skill.query.filter_by(resume_id=resume.id).delete()
                        for idx, skill_data in enumerate(data.get('skills', [])):
                            if skill_data.get('name') and skill_data['name'].strip():
                                skill = Skill(
                                    resume_id=resume.id,
                                    name=skill_data.get('name', ''),
                                    category=skill_data.get('category', ''),
                                    level=skill_data.get('level', ''),
                                    order=idx
                                )
                                db.session.add(skill)
                except Exception as e:
                    app.logger.error(f"Error saving skills: {str(e)}")
                
                # Save projects
                try:
                    if 'projects' in data:
                        Project.query.filter_by(resume_id=resume.id).delete()
                        for idx, proj_data in enumerate(data.get('projects', [])):
                            if proj_data.get('name') and proj_data['name'].strip():
                                project = Project(
                                    resume_id=resume.id,
                                    name=proj_data.get('name', ''),
                                    description=proj_data.get('description', ''),
                                    technologies=proj_data.get('technologies', ''),
                                    link=proj_data.get('link', ''),
                                    order=idx
                                )
                                db.session.add(project)
                except Exception as e:
                    app.logger.error(f"Error saving projects: {str(e)}")
                
                # Save certifications
                try:
                    if 'certifications' in data:
                        Certification.query.filter_by(resume_id=resume.id).delete()
                        for idx, cert_data in enumerate(data.get('certifications', [])):
                            if cert_data.get('name') and cert_data['name'].strip():
                                issue_date = None
                                expiry_date = None
                                
                                if cert_data.get('issue_date') and cert_data['issue_date']:
                                    try:
                                        issue_date = datetime.strptime(cert_data['issue_date'], '%Y-%m-%d')
                                    except (ValueError, TypeError):
                                        issue_date = None
                                
                                if cert_data.get('expiry_date') and cert_data['expiry_date']:
                                    try:
                                        expiry_date = datetime.strptime(cert_data['expiry_date'], '%Y-%m-%d')
                                    except (ValueError, TypeError):
                                        expiry_date = None
                                
                                certification = Certification(
                                    resume_id=resume.id,
                                    name=cert_data.get('name', ''),
                                    issuer=cert_data.get('issuer', ''),
                                    issue_date=issue_date,
                                    expiry_date=expiry_date,
                                    credential_id=cert_data.get('credential_id', ''),
                                    link=cert_data.get('link', ''),
                                    order=idx
                                )
                                db.session.add(certification)
                except Exception as e:
                    app.logger.error(f"Error saving certifications: {str(e)}")
                
                # Save languages
                try:
                    if 'languages' in data:
                        Language.query.filter_by(resume_id=resume.id).delete()
                        for idx, lang_data in enumerate(data.get('languages', [])):
                            if lang_data.get('name') and lang_data['name'].strip():
                                language = Language(
                                    resume_id=resume.id,
                                    name=lang_data.get('name', ''),
                                    proficiency=lang_data.get('proficiency', ''),
                                    order=idx
                                )
                                db.session.add(language)
                except Exception as e:
                    app.logger.error(f"Error saving languages: {str(e)}")
                
                # Save social links
                try:
                    if 'social_links' in data:
                        SocialLink.query.filter_by(resume_id=resume.id).delete()
                        for idx, link_data in enumerate(data.get('social_links', [])):
                            if link_data.get('platform') and link_data.get('url'):
                                social_link = SocialLink(
                                    resume_id=resume.id,
                                    platform=link_data.get('platform', ''),
                                    url=link_data.get('url', ''),
                                    order=idx
                                )
                                db.session.add(social_link)
                except Exception as e:
                    app.logger.error(f"Error saving social links: {str(e)}")
                
                # Commit all changes
                try:
                    db.session.commit()
                    app.logger.info(f"Resume {resume_id} saved successfully")
                    return jsonify({'success': True, 'message': 'Resume saved successfully'})
                except Exception as e:
                    db.session.rollback()
                    app.logger.error(f"Database commit error: {str(e)}")
                    return jsonify({'success': False, 'message': f'Database error: {str(e)}'}), 500
                    
            except Exception as e:
                app.logger.error(f"Error saving resume {resume_id}: {str(e)}")
                app.logger.error(traceback.format_exc())
                db.session.rollback()
                return jsonify({'success': False, 'message': str(e)}), 500
        
        # GET request - load resume data for editing
        try:
            resume_data = get_resume_data(resume)
            has_theme = bool(resume.selected_theme and resume.theme_category)
            return render_template('resume_editor.html', 
                                 resume=resume, 
                                 resume_data=resume_data,
                                 has_theme=has_theme)
        except Exception as e:
            app.logger.error(f"Error loading resume editor: {str(e)}")
            flash('Error loading resume editor', 'danger')
            return redirect(url_for('dashboard'))
    
    @app.route('/resume/<int:resume_id>/delete', methods=['POST'])
    @login_required
    def delete_resume(resume_id):
        resume = Resume.query.get_or_404(resume_id)
        
        if resume.user_id != current_user.id:
            abort(403)
        
        db.session.delete(resume)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Resume deleted successfully'})
    
    @app.route('/resume/<int:resume_id>/duplicate', methods=['POST'])
    @login_required
    def duplicate_resume(resume_id):
        original = Resume.query.get_or_404(resume_id)
        
        if original.user_id != current_user.id:
            abort(403)
        
        # Create new resume
        new_resume = Resume(
            user_id=current_user.id,
            title=f"{original.title} (Copy)",
            selected_theme=original.selected_theme,
            theme_category=original.theme_category,
            theme_settings=original.theme_settings,
            pdf_name=original.pdf_name
        )
        
        db.session.add(new_resume)
        db.session.commit()
        
        # Copy personal info
        if original.personal_info:
            new_personal_info = PersonalInfo(
                resume_id=new_resume.id,
                first_name=original.personal_info.first_name,
                last_name=original.personal_info.last_name,
                email=original.personal_info.email,
                phone=original.personal_info.phone,
                address=original.personal_info.address,
                city=original.personal_info.city,
                country=original.personal_info.country,
                postal_code=original.personal_info.postal_code,
                job_title=original.personal_info.job_title
            )
            db.session.add(new_personal_info)
        
        # Copy other sections
        for model in [Summary, Education, Experience, Skill, Project, Certification, Language, SocialLink]:
            for item in model.query.filter_by(resume_id=original.id):
                new_item = model()
                for column in item.__table__.columns:
                    if column.name not in ['id', 'resume_id']:
                        setattr(new_item, column.name, getattr(item, column.name))
                new_item.resume_id = new_resume.id
                db.session.add(new_item)
        
        db.session.commit()
        flash('Resume duplicated successfully', 'success')
        return redirect(url_for('edit_resume', resume_id=new_resume.id))
    
    @app.route('/resume/<int:resume_id>/theme', methods=['GET', 'POST'])
    @login_required
    def select_theme(resume_id):
        resume = Resume.query.get_or_404(resume_id)
        
        if resume.user_id != current_user.id:
            abort(403)
        
        if request.method == 'POST':
            try:
                data = request.get_json()
                if not data:
                    return jsonify({'success': False, 'message': 'No data provided'}), 400
                
                theme = data.get('theme', 'modern_1')
                category = data.get('category', 'designed')
                
                app.logger.info(f"Saving theme - Resume ID: {resume_id}, Theme: {theme}, Category: {category}")
                
                resume.selected_theme = theme
                resume.theme_category = category
                
                if data.get('theme_settings'):
                    resume.set_theme_settings(data['theme_settings'])
                
                db.session.commit()
                
                return jsonify({
                    'success': True, 
                    'message': 'Theme updated successfully',
                    'theme': theme,
                    'category': category
                })
            except Exception as e:
                app.logger.error(f"Error saving theme: {str(e)}")
                db.session.rollback()
                return jsonify({'success': False, 'message': str(e)}), 500
        
        return redirect(url_for('show_templates', resume_id=resume_id))
    
    @app.route('/resume/<int:resume_id>/preview')
    @login_required
    def preview_resume(resume_id):
        resume = Resume.query.get_or_404(resume_id)
        
        if resume.user_id != current_user.id:
            abort(403)
        
        resume_data = get_resume_data(resume)
        return render_template('preview.html', resume=resume, resume_data=resume_data)
    
    @app.route('/resume/<int:resume_id>/pdf-preview')
    @login_required
    def pdf_preview(resume_id):
        resume = Resume.query.get_or_404(resume_id)
        
        if resume.user_id != current_user.id:
            abort(403)
        
        return render_template('pdf_preview.html', resume=resume)
    
    @app.route('/resume/<int:resume_id>/print-view')
    @login_required
    @no_xframe_options
    def print_view(resume_id):
        """Print-friendly view of the resume (without any UI elements)"""
        resume = Resume.query.get_or_404(resume_id)
        
        if resume.user_id != current_user.id:
            abort(403)
        
        resume_data = get_resume_data(resume)
        
        # Format dates for display
        if 'experiences' in resume_data:
            for exp in resume_data['experiences']:
                exp['start_date_display'] = format_date_for_display(exp.get('start_date'))
                exp['end_date_display'] = 'Present' if exp.get('current') else format_date_for_display(exp.get('end_date'))
        
        if 'education' in resume_data:
            for edu in resume_data['education']:
                edu['start_date_display'] = format_date_for_display(edu.get('start_date'))
                edu['end_date_display'] = 'Present' if edu.get('current') else format_date_for_display(edu.get('end_date'))
        
        if 'certifications' in resume_data:
            for cert in resume_data['certifications']:
                cert['issue_date_display'] = format_year_for_display(cert.get('issue_date'))
                cert['expiry_date_display'] = format_year_for_display(cert.get('expiry_date'))
        
        # Get the theme template
        theme = resume.selected_theme or 'modern_1'
        category = resume.theme_category or 'designed'
        theme_path = f"resume_themes/{category}/{theme}.html"
        
        try:
            # Render just the resume content without the base template
            html_content = render_template(
                theme_path, 
                resume=resume, 
                resume_data=resume_data,
                theme_settings=resume.get_theme_settings() or {},
                preview_mode=True,
                print_mode=True
            )
            
            # Create a minimal HTML wrapper for printing
            full_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{resume.title or 'Resume'} - Print View</title>
    <style>
        /* Reset and print-specific styles */
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            background: white;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.6;
            color: #333;
        }}
        
        /* Print styles */
        @media print {{
            body {{
                margin: 0;
                padding: 0;
            }}
            
            @page {{
                size: A4;
                margin: 1.5cm;
            }}
            
            /* Ensure background colors print */
            * {{
                -webkit-print-color-adjust: exact;
                print-color-adjust: exact;
            }}
        }}
        
        /* Hide any print-specific UI elements if they exist */
        .no-print {{
            display: none;
        }}
    </style>
</head>
<body>
    {html_content}
    <script>
        // Auto-trigger print dialog when page loads
        window.onload = function() {{
            window.print();
        }};
    </script>
</body>
</html>"""
            
            return full_html, 200, {'Content-Type': 'text/html'}
            
        except Exception as e:
            app.logger.error(f"Print view error: {str(e)}")
            error_html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Print View Error</title>
                <style>
                    body {{
                        font-family: Arial, sans-serif;
                        display: flex;
                        justify-content: center;
                        align-items: center;
                        min-height: 100vh;
                        margin: 0;
                        background: #f9fafb;
                    }}
                    .error-container {{
                        text-align: center;
                        padding: 2rem;
                        background: white;
                        border-radius: 12px;
                        max-width: 500px;
                    }}
                    h3 {{ color: #ef4444; }}
                    pre {{
                        background: #f3f4f6;
                        padding: 0.5rem;
                        border-radius: 0.5rem;
                        font-size: 0.75rem;
                        overflow-x: auto;
                        text-align: left;
                    }}
                </style>
            </head>
            <body>
                <div class="error-container">
                    <h3>Error Loading Print View</h3>
                    <p>Unable to load the resume for printing.</p>
                    <pre>{str(e)}</pre>
                </div>
            </body>
            </html>
            """
            return error_html, 200, {'Content-Type': 'text/html'}
    
    @app.route('/resume/<int:resume_id>/download-pdf')
    @login_required
    @no_xframe_options
    def download_pdf(resume_id):
        """Download resume as PDF using xhtml2pdf"""
        resume = Resume.query.get_or_404(resume_id)
        
        if resume.user_id != current_user.id:
            abort(403)
        
        try:
            resume_data = get_resume_data(resume)
            pdf_content = pdf_generator.generate_pdf(resume, resume_data)
            
            filename = resume.pdf_name or resume.title or "resume"
            filename = "".join(c for c in filename if c.isalnum() or c in (' ', '-', '_')).rstrip()
            filename = f"{filename}.pdf"
            
            response = make_response(pdf_content)
            response.headers['Content-Type'] = 'application/pdf'
            response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'
            response.headers['X-Frame-Options'] = 'SAMEORIGIN'
            
            return response
        except Exception as e:
            app.logger.error(f"PDF generation error: {str(e)}")
            app.logger.error(traceback.format_exc())
            flash('Error generating PDF. Please try again.', 'danger')
            return redirect(url_for('edit_resume', resume_id=resume_id))
    
    @app.route('/resume/<int:resume_id>/preview-pdf-content')
    @login_required
    @no_xframe_options
    def preview_pdf_content(resume_id):
        """Get PDF content for preview without downloading"""
        resume = Resume.query.get_or_404(resume_id)
        
        if resume.user_id != current_user.id:
            abort(403)
        
        try:
            resume_data = get_resume_data(resume)
            pdf_content = pdf_generator.generate_pdf(resume, resume_data)
            
            response = make_response(pdf_content)
            response.headers['Content-Type'] = 'application/pdf'
            response.headers['X-Frame-Options'] = 'SAMEORIGIN'
            
            return response
        except Exception as e:
            app.logger.error(f"PDF preview error: {str(e)}")
            return make_response(f"Error generating PDF: {str(e)}", 500)
    
    @app.route('/resume/<int:resume_id>/save-pdf-name', methods=['POST'])
    @login_required
    def save_pdf_name(resume_id):
        resume = Resume.query.get_or_404(resume_id)
        
        if resume.user_id != current_user.id:
            abort(403)
        
        data = request.get_json()
        pdf_name = data.get('pdf_name', '')
        
        resume.pdf_name = pdf_name
        db.session.commit()
        
        return jsonify({'success': True, 'pdf_name': pdf_name})
    
    @app.route('/resume/<int:resume_id>/share')
    @login_required
    def share_resume(resume_id):
        resume = Resume.query.get_or_404(resume_id)
        
        if resume.user_id != current_user.id:
            abort(403)
        
        if not resume.share_token:
            resume.share_token = secrets.token_urlsafe(32)
            db.session.commit()
        
        share_url = url_for('public_resume', token=resume.share_token, _external=True)
        return render_template('share_resume.html', resume=resume, share_url=share_url)
    
    @app.route('/resume/public/<token>')
    @no_xframe_options
    def public_resume(token):
        resume = Resume.query.filter_by(share_token=token).first_or_404()
        resume_data = get_resume_data(resume)
        return render_template('public_resume.html', resume=resume, resume_data=resume_data)
    
    @app.route('/api/resume/<int:resume_id>/load')
    @login_required
    def load_resume_data(resume_id):
        resume = Resume.query.get_or_404(resume_id)
        
        if resume.user_id != current_user.id:
            abort(403)
        
        resume_data = get_resume_data(resume)
        return jsonify({
            'success': True,
            'resume': {
                'id': resume.id,
                'title': resume.title,
                'selected_theme': resume.selected_theme,
                'theme_category': resume.theme_category,
                'theme_settings': resume.get_theme_settings()
            },
            'data': resume_data
        })
    
    @app.route('/api/resume/<int:resume_id>/preview-theme')
    @login_required
    @no_xframe_options
    def preview_theme(resume_id):
        """Preview a specific theme with the resume's data"""
        try:
            resume = Resume.query.get_or_404(resume_id)
            
            if resume.user_id != current_user.id:
                abort(403)
            
            theme = request.args.get('theme', resume.selected_theme or 'modern_1')
            category = request.args.get('category', resume.theme_category or 'designed')
            
            app.logger.info(f"Previewing theme - Resume ID: {resume_id}, Theme: {theme}, Category: {category}")
            
            resume_data = get_resume_data(resume)
            
            # Format dates for display
            if 'experiences' in resume_data:
                for exp in resume_data['experiences']:
                    exp['start_date_display'] = format_date_for_display(exp.get('start_date'))
                    exp['end_date_display'] = 'Present' if exp.get('current') else format_date_for_display(exp.get('end_date'))
            
            if 'education' in resume_data:
                for edu in resume_data['education']:
                    edu['start_date_display'] = format_date_for_display(edu.get('start_date'))
                    edu['end_date_display'] = 'Present' if edu.get('current') else format_date_for_display(edu.get('end_date'))
            
            if 'certifications' in resume_data:
                for cert in resume_data['certifications']:
                    cert['issue_date_display'] = format_year_for_display(cert.get('issue_date'))
                    cert['expiry_date_display'] = format_year_for_display(cert.get('expiry_date'))
            
            theme_path = f"resume_themes/{category}/{theme}.html"
            
            try:
                html_content = render_template(
                    theme_path, 
                    resume=resume, 
                    resume_data=resume_data,
                    theme_settings=resume.get_theme_settings() or {},
                    preview_mode=True
                )
                
                full_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Resume Preview - {theme}</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            background: white;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.6;
            color: #333;
        }}
        
        @media print {{
            body {{
                background: white;
                margin: 0;
                padding: 0;
            }}
        }}
    </style>
</head>
<body>
    {html_content}
</body>
</html>"""
                
                return full_html, 200, {'Content-Type': 'text/html'}
                
            except Exception as template_error:
                app.logger.error(f"Theme template error for {theme_path}: {template_error}")
                error_html = f"""
                <!DOCTYPE html>
                <html>
                <head>
                    <meta charset="UTF-8">
                    <title>Preview Error</title>
                    <style>
                        body {{
                            font-family: Arial, sans-serif;
                            display: flex;
                            justify-content: center;
                            align-items: center;
                            min-height: 100vh;
                            margin: 0;
                            background: #f9fafb;
                        }}
                        .error-container {{
                            text-align: center;
                            padding: 2rem;
                            background: white;
                            border-radius: 12px;
                            max-width: 500px;
                        }}
                        .error-icon {{
                            font-size: 3rem;
                            color: #ef4444;
                        }}
                        details {{
                            margin-top: 1rem;
                            text-align: left;
                        }}
                        pre {{
                            background: #f3f4f6;
                            padding: 0.5rem;
                            border-radius: 0.5rem;
                            font-size: 0.75rem;
                            overflow-x: auto;
                        }}
                    </style>
                </head>
                <body>
                    <div class="error-container">
                        <div class="error-icon">⚠️</div>
                        <h3>Theme Preview Not Available</h3>
                        <p>The theme '{theme}' could not be loaded.</p>
                        <details>
                            <summary>Technical Details</summary>
                            <pre>{str(template_error)}</pre>
                        </details>
                    </div>
                </body>
                </html>
                """
                return error_html, 200, {'Content-Type': 'text/html'}
                
        except Exception as e:
            app.logger.error(f"Theme preview error: {str(e)}")
            error_html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <title>Preview Error</title>
                <style>
                    body {{
                        font-family: Arial, sans-serif;
                        display: flex;
                        justify-content: center;
                        align-items: center;
                        min-height: 100vh;
                        margin: 0;
                        background: #f9fafb;
                    }}
                    .error-container {{
                        text-align: center;
                        padding: 2rem;
                        background: white;
                        border-radius: 12px;
                        max-width: 500px;
                    }}
                    .error-icon {{
                        font-size: 3rem;
                        color: #ef4444;
                    }}
                    pre {{
                        background: #f3f4f6;
                        padding: 0.5rem;
                        border-radius: 0.5rem;
                        font-size: 0.75rem;
                        overflow-x: auto;
                        text-align: left;
                    }}
                </style>
            </head>
            <body>
                <div class="error-container">
                    <div class="error-icon">⚠️</div>
                    <h3>Preview Error</h3>
                    <p>Failed to load theme preview.</p>
                    <pre>{str(e)}</pre>
                </div>
            </body>
            </html>
            """
            return error_html, 200, {'Content-Type': 'text/html'}
    
    @app.route('/api/preview-template')
    @no_xframe_options
    def preview_template():
        """Preview a template with sample data for template gallery"""
        theme = request.args.get('theme', 'modern_1')
        category = request.args.get('category', 'designed')
        
        # Sample resume data
        sample_resume_data = {
            'personal_info': {
                'full_name': 'Sarah Johnson',
                'first_name': 'Sarah',
                'last_name': 'Johnson',
                'job_title': 'Senior Product Designer',
                'email': 'sarah.johnson@example.com',
                'phone': '+1 (555) 123-4567',
                'address': 'San Francisco, CA 94105',
                'city': 'San Francisco',
                'country': 'USA',
                'postal_code': '94105'
            },
            'summaries': [
                {'content': 'Creative and results-driven Product Designer with 8+ years of experience in UI/UX design. Proven track record of delivering user-centered designs that increase engagement and conversion rates.'}
            ],
            'experiences': [
                {
                    'position': 'Senior Product Designer',
                    'company': 'Tech Innovations Inc.',
                    'location': 'San Francisco, CA',
                    'start_date': None,
                    'end_date': None,
                    'start_date_display': 'Jan 2021',
                    'end_date_display': 'Present',
                    'current': True,
                    'description': 'Lead design for flagship product, increased user engagement by 45%'
                },
                {
                    'position': 'UI/UX Designer',
                    'company': 'Creative Solutions',
                    'location': 'New York, NY',
                    'start_date': None,
                    'end_date': None,
                    'start_date_display': 'Jun 2018',
                    'end_date_display': 'Dec 2020',
                    'current': False,
                    'description': 'Designed responsive web applications, improved conversion rates by 30%'
                }
            ],
            'education': [
                {
                    'degree': 'Master of Fine Arts in Design',
                    'field_of_study': 'Interaction Design',
                    'institution': 'California College of the Arts',
                    'start_date': None,
                    'end_date': None,
                    'start_date_display': '2014',
                    'end_date_display': '2016',
                    'current': False
                }
            ],
            'skills': [
                {'name': 'Figma', 'category': 'Design', 'level': 'Expert'},
                {'name': 'Adobe Creative Suite', 'category': 'Design', 'level': 'Expert'},
                {'name': 'User Research', 'category': 'UX', 'level': 'Advanced'}
            ],
            'projects': [
                {
                    'name': 'E-Commerce Redesign',
                    'technologies': 'Figma, User Testing',
                    'description': 'Redesigned checkout flow resulting in 25% increase in conversion rate'
                }
            ],
            'certifications': [],
            'languages': [
                {'name': 'English', 'proficiency': 'Native'},
                {'name': 'Spanish', 'proficiency': 'Professional'}
            ],
            'social_links': []
        }
        
        class MockResume:
            def __init__(self):
                self.selected_theme = theme
                self.theme_category = category
                self.title = "Sample Resume"
            def get_theme_settings(self):
                return {}
        
        mock_resume = MockResume()
        theme_path = f"resume_themes/{category}/{theme}.html"
        
        try:
            rendered_template = render_template(
                theme_path, 
                resume=mock_resume, 
                resume_data=sample_resume_data,
                theme_settings={},
                preview_mode=True
            )
            
            full_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Resume Preview - {theme}</title>
    <style>
        body {{
            background: white;
            margin: 0;
            padding: 0;
        }}
    </style>
</head>
<body>
    {rendered_template}
</body>
</html>"""
            
            return full_html, 200, {'Content-Type': 'text/html'}
            
        except Exception as e:
            error_html = f"""<!DOCTYPE html>
<html>
<head><title>Preview Error</title></head>
<body style="font-family: Arial; padding: 50px; text-align: center;">
    <h2>Preview Error</h2>
    <p>Unable to preview template: {theme}</p>
    <p style="color: #666; font-size: 12px;">{str(e)}</p>
</body>
</html>"""
            return error_html, 200, {'Content-Type': 'text/html'}
    
    @app.route('/test-flash')
    def test_flash():
        flash('This is a success message!', 'success')
        flash('This is a danger/error message!', 'danger')
        flash('This is a warning message!', 'warning')
        flash('This is an info message!', 'info')
        return redirect(url_for('dashboard'))
    
    @app.route('/health')
    def health_check():
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'app_name': app.config.get('APP_NAME', 'Resuma')
        })