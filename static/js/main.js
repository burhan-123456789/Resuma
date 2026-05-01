// Resuma Main JavaScript

document.addEventListener('DOMContentLoaded', function() {
    // Sidebar Toggle (Desktop)
    const sidebarToggle = document.getElementById('sidebarToggle');
    const sidebar = document.getElementById('sidebar');
    
    if (sidebarToggle && sidebar) {
        // Function to update toggle icon
        function updateSidebarIcon() {
            const icon = sidebarToggle.querySelector('i');
            if (sidebar.classList.contains('collapsed')) {
                icon.classList.remove('fa-bars');
                icon.classList.add('fa-chevron-right');
            } else {
                icon.classList.remove('fa-chevron-right');
                icon.classList.add('fa-bars');
            }
        }
        
        // Set initial icon
        updateSidebarIcon();
        
        // Load saved state
        const savedState = localStorage.getItem('sidebarCollapsed');
        if (savedState === 'true') {
            sidebar.classList.add('collapsed');
            updateSidebarIcon();
        }
        
        // Toggle sidebar
        sidebarToggle.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            sidebar.classList.toggle('collapsed');
            updateSidebarIcon();
            
            // Save state
            localStorage.setItem('sidebarCollapsed', sidebar.classList.contains('collapsed'));
            
            // Trigger resize event for any components that need to adjust
            window.dispatchEvent(new Event('resize'));
        });
    }
    
    // Mobile Menu Toggle
    const mobileMenuToggle = document.getElementById('mobileMenuToggle');
    const sidebarOverlay = document.getElementById('sidebarOverlay');
    
    if (mobileMenuToggle && sidebar && sidebarOverlay) {
        // Function to update mobile menu icon
        function updateMobileIcon(isOpen) {
            const icon = mobileMenuToggle.querySelector('i');
            if (isOpen) {
                icon.classList.remove('fa-bars');
                icon.classList.add('fa-times');
            } else {
                icon.classList.remove('fa-times');
                icon.classList.add('fa-bars');
            }
        }
        
        // Open mobile menu
        function openMobileMenu() {
            sidebar.classList.add('mobile-open');
            sidebarOverlay.classList.add('active');
            document.body.style.overflow = 'hidden';
            updateMobileIcon(true);
        }
        
        // Close mobile menu
        function closeMobileMenu() {
            sidebar.classList.remove('mobile-open');
            sidebarOverlay.classList.remove('active');
            document.body.style.overflow = '';
            updateMobileIcon(false);
        }
        
        // Toggle mobile menu
        mobileMenuToggle.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            
            if (sidebar.classList.contains('mobile-open')) {
                closeMobileMenu();
            } else {
                openMobileMenu();
            }
        });
        
        // Close when clicking overlay
        sidebarOverlay.addEventListener('click', closeMobileMenu);
        
        // Close when pressing Escape key
        document.addEventListener('keydown', function(e) {
            if (e.key === 'Escape' && sidebar.classList.contains('mobile-open')) {
                closeMobileMenu();
            }
        });
        
        // Close when clicking nav links (on mobile)
        const navLinks = document.querySelectorAll('.nav-item');
        navLinks.forEach(function(link) {
            link.addEventListener('click', function() {
                if (window.innerWidth <= 768 && sidebar.classList.contains('mobile-open')) {
                    closeMobileMenu();
                }
            });
        });
        
        // Handle window resize
        window.addEventListener('resize', function() {
            if (window.innerWidth > 768) {
                // Close mobile menu if open on desktop
                if (sidebar.classList.contains('mobile-open')) {
                    closeMobileMenu();
                }
                // Ensure body overflow is reset
                document.body.style.overflow = '';
            }
        });
    }
    
    // Password Toggle
    document.querySelectorAll('.toggle-password').forEach(button => {
        button.addEventListener('click', function() {
            const targetId = this.dataset.target;
            const input = document.getElementById(targetId);
            const icon = this.querySelector('i');
            
            if (input && icon) {
                if (input.type === 'password') {
                    input.type = 'text';
                    icon.classList.remove('fa-eye');
                    icon.classList.add('fa-eye-slash');
                } else {
                    input.type = 'password';
                    icon.classList.remove('fa-eye-slash');
                    icon.classList.add('fa-eye');
                }
            }
        });
    });
    
    // Form Validation for Register Form
    const registerForm = document.getElementById('registerForm');
    if (registerForm) {
        registerForm.addEventListener('submit', function(e) {
            const password = document.getElementById('password');
            const confirm = document.getElementById('confirm_password');
            
            if (password && confirm) {
                if (password.value !== confirm.value) {
                    e.preventDefault();
                    showAlert('Passwords do not match', 'danger');
                    return false;
                }
                
                if (!validatePassword(password.value)) {
                    e.preventDefault();
                    return false;
                }
            }
        });
    }
    
    // Theme selection (for templates page)
    window.selectTheme = async function(theme, category, event) {
        const resumeId = document.querySelector('[data-resume-id]')?.getAttribute('data-resume-id');
        if (!resumeId) return;
        
        // Update UI
        document.querySelectorAll('.theme-card').forEach(card => {
            card.classList.remove('selected');
        });
        if (event && event.currentTarget) {
            event.currentTarget.classList.add('selected');
        }
        
        // Preview theme
        try {
            const response = await fetch(`/api/resume/${resumeId}/preview-theme?theme=${theme}&category=${category}`);
            const html = await response.text();
            const previewContent = document.querySelector('.preview-content');
            if (previewContent) {
                previewContent.innerHTML = html;
            }
            
            // Save selection
            await fetch(`/resume/${resumeId}/theme`, {
                method: 'POST',
                headers: { 
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken
                },
                body: JSON.stringify({ theme, category })
            });
        } catch (error) {
            console.error('Theme preview failed:', error);
        }
    };
    
    // PDF Name management
    window.savePdfName = async function(resumeId) {
        const input = document.getElementById('pdfName');
        const pdfName = input ? input.value : '';
        
        try {
            const response = await fetch(`/resume/${resumeId}/save-pdf-name`, {
                method: 'POST',
                headers: { 
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken
                },
                body: JSON.stringify({ pdf_name: pdfName })
            });
            
            const result = await response.json();
            if (result.success) {
                showAlert('PDF name saved successfully', 'success');
            }
        } catch (error) {
            console.error('Failed to save PDF name:', error);
        }
    };
    
    // Copy share link
    window.copyShareLink = function() {
        const shareUrl = document.getElementById('shareUrl');
        if (shareUrl) {
            shareUrl.select();
            document.execCommand('copy');
            showAlert('Share link copied to clipboard!', 'success');
        }
    };
    
    // Helper functions
    function validatePassword(password) {
        const rules = [
            { test: password.length >= 8, message: 'At least 8 characters' },
            { test: /[A-Z]/.test(password), message: 'One uppercase letter' },
            { test: /[a-z]/.test(password), message: 'One lowercase letter' },
            { test: /\d/.test(password), message: 'One number' },
            { test: /[!@#$%^&*(),.?":{}|<>]/.test(password), message: 'One special character' }
        ];
        
        const failed = rules.filter(rule => !rule.test);
        
        if (failed.length > 0) {
            showAlert(`Password must contain: ${failed.map(f => f.message).join(', ')}`, 'warning');
            return false;
        }
        
        return true;
    }
    
    function showAlert(message, type) {
        // Check if flash message container exists
        let flashContainer = document.getElementById('flashMessages');
        
        if (!flashContainer) {
            flashContainer = document.createElement('div');
            flashContainer.id = 'flashMessages';
            flashContainer.className = 'flash-messages';
            document.body.appendChild(flashContainer);
        }
        
        const alertDiv = document.createElement('div');
        alertDiv.className = `flash-message ${type}`;
        alertDiv.innerHTML = `
            <div class="flash-message-content">
                <i class="fas ${getIconForType(type)}"></i>
                <span>${message}</span>
            </div>
            <button type="button" class="flash-close">&times;</button>
        `;
        
        flashContainer.appendChild(alertDiv);
        
        // Add close button functionality
        const closeBtn = alertDiv.querySelector('.flash-close');
        closeBtn.addEventListener('click', function() {
            alertDiv.classList.add('fade-out');
            setTimeout(() => alertDiv.remove(), 300);
        });
        
        // Auto remove after 5 seconds
        setTimeout(() => {
            if (alertDiv.parentElement) {
                alertDiv.classList.add('fade-out');
                setTimeout(() => alertDiv.remove(), 300);
            }
        }, 5000);
    }
    
    function getIconForType(type) {
        switch(type) {
            case 'success': return 'fa-check-circle';
            case 'danger': return 'fa-exclamation-circle';
            case 'warning': return 'fa-exclamation-triangle';
            case 'info': return 'fa-info-circle';
            default: return 'fa-bell';
        }
    }
    
    // Tooltip initialization (if Bootstrap is available)
    if (typeof bootstrap !== 'undefined' && bootstrap.Tooltip) {
        const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
        tooltipTriggerList.map(function(tooltipTriggerEl) {
            return new bootstrap.Tooltip(tooltipTriggerEl);
        });
    }
});

// CSRF Token setup for AJAX requests
const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');
if (csrfToken) {
    window.csrfToken = csrfToken;
    
    // Set up default fetch headers for CSRF
    const originalFetch = window.fetch;
    window.fetch = function(url, options = {}) {
        if (options.method && options.method.toUpperCase() !== 'GET') {
            options.headers = {
                ...options.headers,
                'X-CSRFToken': csrfToken
            };
        }
        return originalFetch.call(this, url, options);
    };
}