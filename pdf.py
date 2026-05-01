# pdf.py - Complete mobile-compatible PDF generator using browser print method
from flask import render_template, make_response, url_for
from datetime import datetime
import os

class PDFGenerator:
    def __init__(self):
        """Initialize PDF generator for mobile environment"""
        pass
    
    def prepare_context(self, resume, resume_data):
        """Prepare context for PDF rendering"""
        theme_settings = resume.get_theme_settings()
        
        context = {
            'resume': resume,
            'resume_data': resume_data,
            'theme_settings': theme_settings,
            'generated_date': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        return context
    
    def generate_html_for_print(self, resume, resume_data):
        """Generate HTML optimized for browser print/Save as PDF"""
        context = self.prepare_context(resume, resume_data)
        
        # Determine theme template path
        category = resume.theme_category or 'designed'
        theme_name = resume.selected_theme or 'modern_1'
        
        theme_path = f"resume_themes/{category}/{theme_name}.html"
        
        # Render the theme template with resume data
        html_content = render_template(theme_path, **context)
        
        # Add print-optimized CSS
        print_css = """
        <style>
            /* Print-optimized styles - ensures perfect PDF from browser */
            @media print {
                /* Remove buttons and interactive elements */
                .no-print, button, .btn, .pdf-controls, .print-button,
                .download-btn, .action-buttons, nav, header:not(.resume-header) {
                    display: none !important;
                }
                
                /* Page settings */
                @page {
                    size: A4;
                    margin: 0.5in;
                }
                
                /* Ensure proper body rendering */
                body {
                    margin: 0;
                    padding: 0;
                    background: white;
                    font-size: 11pt;
                    line-height: 1.4;
                    -webkit-print-color-adjust: exact;
                    print-color-adjust: exact;
                }
                
                /* Preserve colors and backgrounds */
                .resume-header, [style*="background"] {
                    -webkit-print-color-adjust: exact;
                    print-color-adjust: exact;
                }
                
                /* Prevent page breaks inside sections */
                .section, .experience-item, .education-item, .project-item {
                    page-break-inside: avoid;
                    break-inside: avoid;
                }
                
                /* Ensure links are readable */
                a {
                    text-decoration: none;
                    color: black;
                }
                
                a[href]:after {
                    content: none !important;
                }
                
                /* Remove extra spacing */
                .resume-container, .resume {
                    margin: 0;
                    padding: 0;
                    box-shadow: none;
                }
                
                /* Ensure two-column layouts work */
                .two-column, .two-columns, .grid {
                    display: block !important;
                }
                
                .left-column, .right-column, .sidebar, .main-content {
                    width: 100% !important;
                    display: block !important;
                }
            }
            
            /* Screen styles for print preview button */
            .print-button-container {
                text-align: center;
                padding: 20px;
                background: #f5f5f5;
                border-bottom: 1px solid #ddd;
            }
            
            .print-button {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                border: none;
                padding: 12px 30px;
                font-size: 16px;
                border-radius: 8px;
                cursor: pointer;
                font-weight: 600;
                margin: 10px;
                transition: transform 0.2s;
            }
            
            .print-button:hover {
                transform: scale(1.02);
            }
            
            .print-button i {
                margin-right: 8px;
            }
        </style>
        """
        
        # Add print button at the top of the page
        print_button_html = """
        <div class="print-button-container no-print">
            <button class="print-button" onclick="window.print();">
                📄 Save as PDF / Print
            </button>
            <button class="print-button" onclick="history.back();" style="background: #6c757d;">
                ← Back to Editor
            </button>
        </div>
        """
        
        # Insert print CSS and button into HTML
        if '</head>' in html_content:
            html_content = html_content.replace('</head>', print_css + '</head>')
        else:
            html_content = print_css + html_content
        
        # Insert print button after body opening
        if '<body' in html_content:
            html_content = html_content.replace('<body', '<body', 1)
            # Find the first > after body tag
            body_end = html_content.find('>', html_content.find('<body'))
            if body_end != -1:
                html_content = html_content[:body_end+1] + print_button_html + html_content[body_end+1:]
        
        return html_content
    
    def generate_pdf_response(self, resume, resume_data, filename=None, method='browser'):
        """
        Generate HTML page that user can save as PDF using browser's print function
        
        Args:
            resume: Resume object
            resume_data: Resume data dictionary
            filename: PDF filename (used for browser download)
            method: Generation method (only 'browser' supported on mobile)
        """
        html_content = self.generate_html_for_print(resume, resume_data)
        
        if not filename:
            filename = resume.pdf_name or resume.title or "resume"
        
        # Sanitize filename
        filename = "".join(c for c in filename if c.isalnum() or c in (' ', '-', '_')).rstrip()
        
        # Return HTML page with instructions to save as PDF
        response = make_response(html_content)
        response.headers['Content-Type'] = 'text/html'
        
        return response
    
    def generate_pdf_binary(self, resume, resume_data):
        """
        Generate actual PDF binary (fallback - uses reportlab without styling)
        This is kept for automatic PDF generation needs
        """
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.units import cm
            from bs4 import BeautifulSoup
            import io
            import re
            
            context = self.prepare_context(resume, resume_data)
            
            category = resume.theme_category or 'designed'
            theme_name = resume.selected_theme or 'modern_1'
            theme_path = f"resume_themes/{category}/{theme_name}.html"
            
            html_content = render_template(theme_path, **context)
            
            buffer = io.BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=A4, 
                                   topMargin=1*cm, bottomMargin=1*cm,
                                   leftMargin=1*cm, rightMargin=1*cm)
            story = []
            styles = getSampleStyleSheet()
            
            # Create custom styles
            title_style = ParagraphStyle('CustomTitle', parent=styles['Normal'], 
                                        fontSize=16, spaceAfter=10, alignment=1)
            heading_style = ParagraphStyle('CustomHeading', parent=styles['Normal'], 
                                          fontSize=12, spaceBefore=8, spaceAfter=4)
            normal_style = ParagraphStyle('CustomNormal', parent=styles['Normal'], 
                                         fontSize=9, spaceAfter=3, leading=12)
            
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Extract name
            name_selectors = ['.name', '.full-name', 'h1.name', '.resume-name']
            name = None
            for selector in name_selectors:
                name_tag = soup.select_one(selector)
                if name_tag:
                    name = name_tag.get_text(strip=True)
                    break
            
            if name:
                story.append(Paragraph(name, title_style))
                story.append(Spacer(1, 0.3*cm))
            
            # Extract sections
            sections = soup.find_all('div', class_=re.compile('section'))
            if not sections:
                sections = soup.find_all('section')
            
            for section in sections:
                # Get section title
                title_tag = section.find(['h2', 'h3'], class_=re.compile('title'))
                if not title_tag:
                    title_tag = section.find(['h2', 'h3'])
                
                if title_tag:
                    story.append(Paragraph(title_tag.get_text(strip=True), heading_style))
                
                # Get content
                for item in section.find_all('div', class_=re.compile('item|entry|experience-item')):
                    text = item.get_text(strip=True)
                    if text and len(text) < 500 and len(text) > 10:
                        story.append(Paragraph(text[:300], normal_style))
                        story.append(Spacer(1, 0.15*cm))
            
            if not story:
                # Fallback: Get all text
                body_text = soup.get_text()
                lines = body_text.split('\n')
                for line in lines[:30]:
                    if line.strip() and len(line.strip()) < 200:
                        story.append(Paragraph(line.strip(), normal_style))
            
            doc.build(story)
            pdf_content = buffer.getvalue()
            buffer.close()
            
            return pdf_content
            
        except Exception as e:
            # Ultra minimal fallback
            return self._create_minimal_pdf(f"PDF Generation requires browser print. Error: {str(e)}")
    
    def _create_minimal_pdf(self, error_msg):
        """Create a minimal PDF with error message"""
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.platypus import SimpleDocTemplate, Paragraph
            from reportlab.lib.styles import getSampleStyleSheet
            import io
            
            buffer = io.BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=A4)
            story = []
            styles = getSampleStyleSheet()
            story.append(Paragraph(error_msg, styles['Normal']))
            doc.build(story)
            return buffer.getvalue()
        except:
            return b'%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R >>\nendobj\n4 0 obj\n<< /Length 50 >>\nstream\nBT /F1 12 Tf 50 750 Td (Use browser print to save as PDF) Tj ET\nendstream\nendobj\nxref\n0 5\n0000000000 65535 f\n0000000009 00000 n\n0000000058 00000 n\n0000000115 00000 n\n0000000208 00000 n\ntrailer\n<< /Size 5 /Root 1 0 R >>\nstartxref\n300\n%%EOF'


def get_resume_data(resume):
    """Get all resume data structured for templates"""
    data = {
        'personal_info': None,
        'summaries': [],
        'education': [],
        'experiences': [],
        'skills': [],
        'projects': [],
        'certifications': [],
        'languages': [],
        'social_links': []
    }
    
    if resume.personal_info:
        data['personal_info'] = {
            'first_name': resume.personal_info.first_name or '',
            'last_name': resume.personal_info.last_name or '',
            'full_name': f"{resume.personal_info.first_name or ''} {resume.personal_info.last_name or ''}".strip(),
            'email': resume.personal_info.email or '',
            'phone': resume.personal_info.phone or '',
            'address': resume.personal_info.address or '',
            'city': resume.personal_info.city or '',
            'country': resume.personal_info.country or '',
            'postal_code': resume.personal_info.postal_code or '',
            'job_title': resume.personal_info.job_title or ''
        }
    else:
        data['personal_info'] = {
            'first_name': '', 'last_name': '', 'full_name': '',
            'email': '', 'phone': '', 'address': '', 'city': '',
            'country': '', 'postal_code': '', 'job_title': ''
        }
    
    # Sort by order
    data['summaries'] = sorted([{
        'id': s.id,
        'content': s.content or ''
    } for s in resume.summaries], key=lambda x: x.get('order', 0) if isinstance(x, dict) else 0)
    
    data['education'] = sorted([{
        'id': e.id,
        'institution': e.institution or '',
        'degree': e.degree or '',
        'field_of_study': e.field_of_study or '',
        'start_date': e.start_date,
        'end_date': e.end_date,
        'current': e.current,
        'description': e.description or ''
    } for e in resume.education], key=lambda x: x.get('order', 0) if isinstance(x, dict) else 0)
    
    data['experiences'] = sorted([{
        'id': exp.id,
        'company': exp.company or '',
        'position': exp.position or '',
        'location': exp.location or '',
        'start_date': exp.start_date,
        'end_date': exp.end_date,
        'current': exp.current,
        'description': exp.description or ''
    } for exp in resume.experiences], key=lambda x: x.get('order', 0) if isinstance(x, dict) else 0)
    
    data['skills'] = sorted([{
        'id': s.id,
        'name': s.name or '',
        'category': s.category or '',
        'level': s.level or ''
    } for s in resume.skills], key=lambda x: x.get('order', 0) if isinstance(x, dict) else 0)
    
    data['projects'] = sorted([{
        'id': p.id,
        'name': p.name or '',
        'description': p.description or '',
        'technologies': p.technologies or '',
        'link': p.link or '',
        'start_date': p.start_date,
        'end_date': p.end_date
    } for p in resume.projects], key=lambda x: x.get('order', 0) if isinstance(x, dict) else 0)
    
    data['certifications'] = sorted([{
        'id': c.id,
        'name': c.name or '',
        'issuer': c.issuer or '',
        'issue_date': c.issue_date,
        'expiry_date': c.expiry_date,
        'credential_id': c.credential_id or '',
        'link': c.link or ''
    } for c in resume.certifications], key=lambda x: x.get('order', 0) if isinstance(x, dict) else 0)
    
    data['languages'] = sorted([{
        'id': l.id,
        'name': l.name or '',
        'proficiency': l.proficiency or ''
    } for l in resume.languages], key=lambda x: x.get('order', 0) if isinstance(x, dict) else 0)
    
    data['social_links'] = sorted([{
        'id': s.id,
        'platform': s.platform or '',
        'url': s.url or ''
    } for s in resume.social_links], key=lambda x: x.get('order', 0) if isinstance(x, dict) else 0)
    
    return data