// MTPL Unified Launcher - Main JavaScript

// Auto-dismiss success alerts after 5 seconds (but keep error/warning alerts visible)
document.addEventListener('DOMContentLoaded', function() {
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach(alert => {
        // Only auto-dismiss success and info alerts, not errors or warnings
        if (alert.classList.contains('alert-success') || alert.classList.contains('alert-info')) {
            setTimeout(() => {
                alert.style.opacity = '0';
                setTimeout(() => alert.remove(), 300);
            }, 5000);
        }
    });
});

// Navbar dropdown functionality
document.addEventListener('DOMContentLoaded', function() {
    const dropdowns = document.querySelectorAll('.navbar-dropdown');
    
    dropdowns.forEach(dropdown => {
        dropdown.addEventListener('click', function(e) {
            e.preventDefault();
            const menu = this.querySelector('.navbar-dropdown-menu');
            if (menu) {
                menu.style.display = menu.style.display === 'block' ? 'none' : 'block';
            }
        });
    });
    
    // Close dropdowns when clicking outside
    document.addEventListener('click', function(e) {
        if (!e.target.closest('.navbar-dropdown')) {
            document.querySelectorAll('.navbar-dropdown-menu').forEach(menu => {
                menu.style.display = 'none';
            });
        }
    });
});

// Utility function to show loading state
function showLoading(element, message = 'Loading...') {
    if (element) {
        element.innerHTML = `<div class="loading">${message}</div>`;
    }
}

// Utility function to show error state
function showError(element, message = 'An error occurred') {
    if (element) {
        element.innerHTML = `<div class="alert alert-error">${message}</div>`;
    }
}

// Utility function to format date/time
function formatDateTime(dateString) {
    if (!dateString) return 'Never';
    
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMins / 60);
    const diffDays = Math.floor(diffHours / 24);
    
    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins} minute${diffMins > 1 ? 's' : ''} ago`;
    if (diffHours < 24) return `${diffHours} hour${diffHours > 1 ? 's' : ''} ago`;
    if (diffDays < 7) return `${diffDays} day${diffDays > 1 ? 's' : ''} ago`;
    
    return date.toLocaleDateString() + ' ' + date.toLocaleTimeString();
}

// API helper function
async function apiCall(url, options = {}) {
    try {
        const response = await fetch(url, {
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            },
            ...options
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.error || `HTTP error! status: ${response.status}`);
        }
        
        return data;
    } catch (error) {
        console.error('API call failed:', error);
        throw error;
    }
}

// Show success message
function showSuccess(message) {
    const container = document.querySelector('.alerts-container') || document.querySelector('.container');
    if (container) {
        const alert = document.createElement('div');
        alert.className = 'alert alert-success';
        alert.innerHTML = `${message} <button type="button" class="alert-close" onclick="this.parentElement.remove()">&times;</button>`;
        container.insertBefore(alert, container.firstChild);
        
        setTimeout(() => {
            alert.style.opacity = '0';
            setTimeout(() => alert.remove(), 300);
        }, 5000);
    }
}

// Show error message
function showErrorMessage(message) {
    const container = document.querySelector('.alerts-container') || document.querySelector('.container');
    if (container) {
        const alert = document.createElement('div');
        alert.className = 'alert alert-error';
        alert.innerHTML = `${message} <button type="button" class="alert-close" onclick="this.parentElement.remove()">&times;</button>`;
        container.insertBefore(alert, container.firstChild);
        
        setTimeout(() => {
            alert.style.opacity = '0';
            setTimeout(() => alert.remove(), 300);
        }, 5000);
    }
}

// Confirm dialog
function confirm2(message) {
    return window.confirm(message);
}
