/**
 * =================================================================
 * MTPL SOFTWARE SUITE - MASTER UI JAVASCRIPT
 * Unified JavaScript Library for All Applications
 * Version: 2.0
 * Last Updated: November 2025
 * =================================================================
 */

// ============================================
// 1. MASTER TABLE SYSTEM WITH SORTING & FILTERING
// ============================================

class MTPLTable {
    constructor(tableId, options = {}) {
        this.table = document.getElementById(tableId);
        if (!this.table) {
            return;
        }
        
        this.options = {
            sortable: options.sortable !== false,
            filterable: options.filterable !== false,
            paginate: options.paginate !== false,
            rowsPerPage: options.rowsPerPage || 15,
            searchInputId: options.searchInputId || null,
            filterInputs: options.filterInputs || [],
            emptyStateElement: options.emptyStateElement || null,
            onSort: options.onSort || null,
            onFilter: options.onFilter || null,
            onPageChange: options.onPageChange || null
        };
        
        this.currentSort = { field: null, direction: 'asc' };
        this.currentPage = 1;
        this.filteredRows = [];
        this.allRows = [];
        
        this.init();
    }
    
    init() {
        this.storeAllRows();
        
        if (this.options.sortable) {
            this.initSorting();
        }
        
        if (this.options.filterable) {
            this.initFiltering();
        }
        
        if (this.options.paginate) {
            this.initPagination();
        }
    }
    
    storeAllRows() {
        const tbody = this.table.querySelector('tbody');
        if (tbody) {
            this.allRows = Array.from(tbody.querySelectorAll('tr'));
            this.filteredRows = [...this.allRows];
        }
    }
    
    initSorting() {
        const headers = this.table.querySelectorAll('thead th[data-sort]');
        headers.forEach(header => {
            header.classList.add('sortable', 'cursor-pointer');
            
            // Add sort icon if not present
            if (!header.querySelector('i.fa-sort')) {
                const icon = document.createElement('i');
                icon.className = 'fas fa-sort ms-1';
                header.appendChild(icon);
            }
            
            header.addEventListener('click', () => this.handleSort(header));
        });
    }
    
    handleSort(header) {
        const field = header.getAttribute('data-sort');
        
        // Toggle sort direction
        if (this.currentSort.field === field) {
            this.currentSort.direction = this.currentSort.direction === 'asc' ? 'desc' : 'asc';
        } else {
            this.currentSort.field = field;
            this.currentSort.direction = 'asc';
        }
        
        this.sortRows();
        this.updateSortIcons();
        this.render();
        
        // Callback
        if (this.options.onSort) {
            this.options.onSort(this.currentSort);
        }
    }
    
    sortRows() {
        const field = this.currentSort.field;
        const direction = this.currentSort.direction;
        const columnIndex = this.getColumnIndex(field);
        
        if (columnIndex === -1) return;
        
        this.filteredRows.sort((a, b) => {
            const aCell = a.cells[columnIndex];
            const bCell = b.cells[columnIndex];
            
            if (!aCell || !bCell) return 0;
            
            const aValue = aCell.getAttribute('data-sort-value') || aCell.textContent.trim();
            const bValue = bCell.getAttribute('data-sort-value') || bCell.textContent.trim();
            
            // Try numeric comparison
            const aNum = parseFloat(aValue);
            const bNum = parseFloat(bValue);
            
            if (!isNaN(aNum) && !isNaN(bNum)) {
                return direction === 'asc' ? aNum - bNum : bNum - aNum;
            }
            
            // String comparison
            return direction === 'asc' 
                ? aValue.localeCompare(bValue)
                : bValue.localeCompare(aValue);
        });
    }
    
    getColumnIndex(field) {
        const headers = Array.from(this.table.querySelectorAll('thead th'));
        return headers.findIndex(th => th.getAttribute('data-sort') === field);
    }
    
    updateSortIcons() {
        const headers = this.table.querySelectorAll('thead th[data-sort]');
        headers.forEach(header => {
            const icon = header.querySelector('i');
            const field = header.getAttribute('data-sort');
            
            header.classList.remove('sorted-asc', 'sorted-desc');
            
            if (field === this.currentSort.field) {
                icon.className = this.currentSort.direction === 'asc' 
                    ? 'fas fa-sort-up ms-1' 
                    : 'fas fa-sort-down ms-1';
                header.classList.add(`sorted-${this.currentSort.direction}`);
            } else {
                icon.className = 'fas fa-sort ms-1';
            }
        });
    }
    
    initFiltering() {
        // Search input
        if (this.options.searchInputId) {
            const searchInput = document.getElementById(this.options.searchInputId);
            if (searchInput) {
                searchInput.addEventListener('input', () => this.handleFilter());
            }
        }
        
        // Filter inputs
        this.options.filterInputs.forEach(inputId => {
            const input = document.getElementById(inputId);
            if (input) {
                input.addEventListener('change', () => this.handleFilter());
            }
        });
    }
    
    handleFilter() {
        this.filteredRows = this.allRows.filter(row => {
            // Search filter
            if (this.options.searchInputId) {
                const searchInput = document.getElementById(this.options.searchInputId);
                const searchValue = searchInput ? searchInput.value.toLowerCase() : '';
                
                if (searchValue) {
                    const rowText = row.textContent.toLowerCase();
                    if (!rowText.includes(searchValue)) {
                        return false;
                    }
                }
            }
            
            // Custom filters
            for (const inputId of this.options.filterInputs) {
                const input = document.getElementById(inputId);
                if (!input || !input.value) continue;
                
                const filterValue = input.value.toLowerCase();
                const filterField = input.getAttribute('data-filter-field');
                
                if (filterField) {
                    const cell = row.querySelector(`[data-field="${filterField}"]`);
                    if (cell) {
                        const cellValue = cell.textContent.toLowerCase();
                        if (!cellValue.includes(filterValue)) {
                            return false;
                        }
                    }
                }
            }
            
            return true;
        });
        
        this.currentPage = 1;
        this.render();
        
        // Callback
        if (this.options.onFilter) {
            this.options.onFilter(this.filteredRows.length, this.allRows.length);
        }
    }
    
    initPagination() {
        // Pagination will be rendered dynamically in render()
    }
    
    render() {
        const tbody = this.table.querySelector('tbody');
        if (!tbody) return;
        
        // Clear tbody
        tbody.innerHTML = '';
        
        // Check if empty
        if (this.filteredRows.length === 0) {
            this.showEmptyState();
            return;
        } else {
            this.hideEmptyState();
        }
        
        // Pagination
        if (this.options.paginate) {
            const startIndex = (this.currentPage - 1) * this.options.rowsPerPage;
            const endIndex = startIndex + this.options.rowsPerPage;
            const rowsToShow = this.filteredRows.slice(startIndex, endIndex);
            
            rowsToShow.forEach(row => tbody.appendChild(row.cloneNode(true)));
            
            this.renderPagination();
        } else {
            this.filteredRows.forEach(row => tbody.appendChild(row.cloneNode(true)));
        }
    }
    
    renderPagination() {
        // Find or create pagination container
        let paginationContainer = this.table.parentElement.querySelector('.mtpl-pagination-container');
        
        if (!paginationContainer) {
            paginationContainer = document.createElement('div');
            paginationContainer.className = 'mtpl-pagination-container d-flex justify-content-center align-items-center mt-4';
            this.table.parentElement.appendChild(paginationContainer);
        }
        
        const totalPages = Math.ceil(this.filteredRows.length / this.options.rowsPerPage);
        
        if (totalPages <= 1) {
            paginationContainer.innerHTML = '';
            return;
        }
        
        let html = '<ul class="mtpl-pagination">';
        
        // Previous button
        html += `
            <li class="mtpl-pagination-item">
                <a class="mtpl-pagination-link ${this.currentPage === 1 ? 'disabled' : ''}" 
                   data-page="${this.currentPage - 1}">
                    <i class="fas fa-chevron-left"></i>
                </a>
            </li>
        `;
        
        // Page numbers
        for (let i = 1; i <= totalPages; i++) {
            // Show first, last, current, and adjacent pages
            if (i === 1 || i === totalPages || (i >= this.currentPage - 1 && i <= this.currentPage + 1)) {
                html += `
                    <li class="mtpl-pagination-item">
                        <a class="mtpl-pagination-link ${i === this.currentPage ? 'active' : ''}" 
                           data-page="${i}">
                            ${i}
                        </a>
                    </li>
                `;
            } else if (i === this.currentPage - 2 || i === this.currentPage + 2) {
                html += `
                    <li class="mtpl-pagination-item">
                        <span class="mtpl-pagination-link disabled">...</span>
                    </li>
                `;
            }
        }
        
        // Next button
        html += `
            <li class="mtpl-pagination-item">
                <a class="mtpl-pagination-link ${this.currentPage === totalPages ? 'disabled' : ''}" 
                   data-page="${this.currentPage + 1}">
                    <i class="fas fa-chevron-right"></i>
                </a>
            </li>
        `;
        
        html += '</ul>';
        
        paginationContainer.innerHTML = html;
        
        // Add click handlers
        paginationContainer.querySelectorAll('.mtpl-pagination-link').forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                if (link.classList.contains('disabled') || link.classList.contains('active')) return;
                
                const page = parseInt(link.getAttribute('data-page'));
                this.goToPage(page);
            });
        });
    }
    
    goToPage(page) {
        const totalPages = Math.ceil(this.filteredRows.length / this.options.rowsPerPage);
        
        if (page < 1 || page > totalPages) return;
        
        this.currentPage = page;
        this.render();
        
        // Callback
        if (this.options.onPageChange) {
            this.options.onPageChange(this.currentPage, totalPages);
        }
        
        // Scroll to top of table
        this.table.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
    
    showEmptyState() {
        if (this.options.emptyStateElement) {
            const element = document.getElementById(this.options.emptyStateElement);
            if (element) {
                element.style.display = 'block';
            }
        }
    }
    
    hideEmptyState() {
        if (this.options.emptyStateElement) {
            const element = document.getElementById(this.options.emptyStateElement);
            if (element) {
                element.style.display = 'none';
            }
        }
    }
    
    refresh() {
        this.storeAllRows();
        this.handleFilter();
    }
}

// ============================================
// 2. MASTER MODAL SYSTEM
// ============================================

class MTPLModal {
    constructor() {
        this.createModal();
    }
    
    createModal() {
        // Check if modal already exists
        if (document.getElementById('mtplMasterModalBackdrop')) return;
        
        const modalHTML = `
            <div id="mtplMasterModalBackdrop" class="mtpl-modal-backdrop" style="display: none; visibility: hidden; pointer-events: none;">
                <div class="mtpl-modal mtpl-modal-md">
                    <div class="mtpl-modal-header">
                        <h5 class="mtpl-modal-title" id="mtplMasterModalTitle">Modal Title</h5>
                        <button type="button" class="mtpl-modal-close" onclick="closeMTPLModal()">
                            <i class="fas fa-times"></i>
                        </button>
                    </div>
                    <div class="mtpl-modal-body" id="mtplMasterModalBody">
                        Modal body content
                    </div>
                    <div class="mtpl-modal-footer" id="mtplMasterModalFooter">
                    </div>
                </div>
            </div>
        `;
        
        document.body.insertAdjacentHTML('beforeend', modalHTML);
        
        // Close on backdrop click
        document.getElementById('mtplMasterModalBackdrop').addEventListener('click', (e) => {
            if (e.target.id === 'mtplMasterModalBackdrop') {
                this.close();
            }
        });
        
        // Close on ESC key
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                const backdrop = document.getElementById('mtplMasterModalBackdrop');
                if (backdrop && backdrop.style.display === 'flex') {
                    this.close();
                }
            }
        });
    }
    
    open(options = {}) {
        const backdrop = document.getElementById('mtplMasterModalBackdrop');
        if (!backdrop) {
            return;
        }
        
        const modal = backdrop.querySelector('.mtpl-modal');
        const title = document.getElementById('mtplMasterModalTitle');
        const body = document.getElementById('mtplMasterModalBody');
        const footer = document.getElementById('mtplMasterModalFooter');
        
        
        // Set title
        title.innerHTML = options.title || 'Modal';
        
        // Set body
        if (typeof options.body === 'string') {
            body.innerHTML = options.body;
        } else if (options.body instanceof HTMLElement) {
            body.innerHTML = '';
            body.appendChild(options.body);
        }
        
        // Set size
        modal.className = 'mtpl-modal';
        if (options.size === 'small') {
            modal.classList.add('mtpl-modal-sm');
        } else if (options.size === 'medium') {
            modal.classList.add('mtpl-modal-md');
        } else if (options.size === 'large') {
            modal.classList.add('mtpl-modal-lg');
        } else {
            modal.classList.add('mtpl-modal-md'); // Default
        }
        
        // Set footer buttons
        footer.innerHTML = '';
        if (options.buttons && options.buttons.length > 0) {
            options.buttons.forEach(btn => {
                const button = document.createElement('button');
                button.className = `mtpl-btn mtpl-btn-${btn.class || 'primary'}`;
                
                if (btn.icon) {
                    button.innerHTML = `<i class="fas fa-${btn.icon}"></i> ${btn.text}`;
                } else {
                    button.textContent = btn.text;
                }
                
                if (btn.onclick) {
                    button.addEventListener('click', btn.onclick);
                }
                
                footer.appendChild(button);
            });
        }
        
        // Show modal - ensure all styles are set with proper z-index
        backdrop.style.display = 'flex';
        backdrop.style.visibility = 'visible';
        backdrop.style.pointerEvents = 'auto';
        backdrop.style.zIndex = '999999';
        backdrop.style.opacity = '1';
        
        requestAnimationFrame(() => {
            backdrop.classList.add('show');
        });
        
        document.body.style.overflow = 'hidden';
        document.body.classList.add('modal-open');
    }
    
    close() {
        const backdrop = document.getElementById('mtplMasterModalBackdrop');
        if (!backdrop) return;
        
        backdrop.classList.remove('show');
        
        // Immediately restore body and disable backdrop
        document.body.style.overflow = '';
        document.body.style.pointerEvents = 'auto';
        document.body.classList.remove('modal-open');
        
        backdrop.style.pointerEvents = 'none';
        backdrop.style.zIndex = '-9999';
        backdrop.style.opacity = '0';
        backdrop.style.display = 'none';
        backdrop.style.visibility = 'hidden';
        
        // Force cleanup immediately and after animation
        cleanupModalBackdrops();
        setTimeout(cleanupModalBackdrops, 100);
        setTimeout(cleanupModalBackdrops, 350);
    }
}

// Global modal instance
const MTPLModalInstance = new MTPLModal();

// Convenience function
function openMTPLModal(options) {
    MTPLModalInstance.open(options);
}

function closeMTPLModal() {
    MTPLModalInstance.close();
}

// ============================================
// 3. MASTER TOAST SYSTEM
// ============================================

class MTPLToast {
    constructor() {
        this.createContainer();
    }
    
    createContainer() {
        if (document.getElementById('mtplToastContainer')) return;
        
        const container = document.createElement('div');
        container.id = 'mtplToastContainer';
        container.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            z-index: 1000500;
            min-width: 300px;
            max-width: 500px;
        `;
        document.body.appendChild(container);
    }
    
    show(message, type = 'info', duration = 5000) {
        const container = document.getElementById('mtplToastContainer');
        
        const toast = document.createElement('div');
        toast.className = `mtpl-toast mtpl-toast-${type}`;
        toast.style.cssText = `
            background: white;
            border-radius: 0.75rem;
            box-shadow: 0 10px 25px rgba(0, 0, 0, 0.15);
            padding: 1rem 1.25rem;
            margin-bottom: 1rem;
            display: flex;
            align-items: center;
            gap: 1rem;
            border-left: 4px solid;
            animation: mtpl-slideDown 0.3s ease-out;
        `;
        
        // Icon and color based on type
        let icon, borderColor, iconColor;
        switch(type) {
            case 'success':
                icon = 'check-circle';
                borderColor = '#10b981';
                iconColor = '#10b981';
                break;
            case 'error':
            case 'danger':
                icon = 'exclamation-circle';
                borderColor = '#ef4444';
                iconColor = '#ef4444';
                break;
            case 'warning':
                icon = 'exclamation-triangle';
                borderColor = '#f59e0b';
                iconColor = '#f59e0b';
                break;
            case 'info':
            default:
                icon = 'info-circle';
                borderColor = '#3b82f6';
                iconColor = '#3b82f6';
                break;
        }
        
        toast.style.borderLeftColor = borderColor;
        
        toast.innerHTML = `
            <div style="flex-shrink: 0;">
                <i class="fas fa-${icon}" style="font-size: 1.5rem; color: ${iconColor};"></i>
            </div>
            <div style="flex-grow: 1; color: #1f2937; font-size: 0.875rem;">
                ${message}
            </div>
            <button onclick="this.parentElement.remove()" 
                    style="flex-shrink: 0; background: none; border: none; color: #6b7280; cursor: pointer; font-size: 1.25rem; padding: 0; line-height: 1;">
                <i class="fas fa-times"></i>
            </button>
        `;
        
        container.appendChild(toast);
        
        // Auto remove
        if (duration > 0) {
            setTimeout(() => {
                toast.style.animation = 'mtpl-fadeOut 0.3s ease-out';
                setTimeout(() => toast.remove(), 300);
            }, duration);
        }
    }
}

// Global toast instance
const MTPLToastInstance = new MTPLToast();

// Convenience function
function showMTPLToast(message, type = 'info', duration = 5000) {
    MTPLToastInstance.show(message, type, duration);
}

// ============================================
// 4. LOADING OVERLAY SYSTEM
// ============================================

function showMTPLLoading(message = 'Loading...') {
    // Remove existing overlay if present
    const existing = document.getElementById('mtplLoadingOverlay');
    if (existing) existing.remove();
    
    const overlay = document.createElement('div');
    overlay.id = 'mtplLoadingOverlay';
    overlay.className = 'mtpl-loading-overlay';
    overlay.innerHTML = `
        <div class="mtpl-spinner mtpl-spinner-lg"></div>
        <div class="mtpl-loading-text">${message}</div>
    `;
    
    document.body.appendChild(overlay);
    document.body.style.overflow = 'hidden';
}

function hideMTPLLoading() {
    const overlay = document.getElementById('mtplLoadingOverlay');
    if (overlay) {
        overlay.style.animation = 'mtpl-fadeOut 0.3s ease-out';
        setTimeout(() => {
            overlay.remove();
            document.body.style.overflow = '';
        }, 300);
    }
}

// ============================================
// 5. FORM VALIDATION SYSTEM
// ============================================

function validateMTPLForm(formId) {
    const form = document.getElementById(formId);
    if (!form) return false;
    
    let isValid = true;
    
    // Get all required inputs
    const requiredInputs = form.querySelectorAll('[required]');
    
    requiredInputs.forEach(input => {
        const value = input.value.trim();
        
        // Remove previous validation classes
        input.classList.remove('is-valid', 'is-invalid');
        
        if (!value) {
            input.classList.add('is-invalid');
            isValid = false;
        } else {
            input.classList.add('is-valid');
        }
    });
    
    return isValid;
}

function clearMTPLFormValidation(formId) {
    const form = document.getElementById(formId);
    if (!form) return;
    
    const inputs = form.querySelectorAll('.is-valid, .is-invalid');
    inputs.forEach(input => {
        input.classList.remove('is-valid', 'is-invalid');
    });
}

// ============================================
// 6. UTILITY FUNCTIONS
// ============================================

// Debounce function for search inputs
function mtplDebounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Format date
function mtplFormatDate(date, format = 'YYYY-MM-DD') {
    if (!(date instanceof Date)) {
        date = new Date(date);
    }
    
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    const hours = String(date.getHours()).padStart(2, '0');
    const minutes = String(date.getMinutes()).padStart(2, '0');
    const seconds = String(date.getSeconds()).padStart(2, '0');
    
    return format
        .replace('YYYY', year)
        .replace('MM', month)
        .replace('DD', day)
        .replace('HH', hours)
        .replace('mm', minutes)
        .replace('ss', seconds);
}

// Format number with thousands separator
function mtplFormatNumber(number, decimals = 0) {
    return Number(number).toLocaleString('en-US', {
        minimumFractionDigits: decimals,
        maximumFractionDigits: decimals
    });
}

// Copy to clipboard
function mtplCopyToClipboard(text) {
    if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(text).then(() => {
            showMTPLToast('Copied to clipboard!', 'success', 2000);
        }).catch(err => {
            showMTPLToast('Failed to copy to clipboard', 'error');
        });
    } else {
        // Fallback for older browsers
        const textarea = document.createElement('textarea');
        textarea.value = text;
        textarea.style.position = 'fixed';
        textarea.style.opacity = '0';
        document.body.appendChild(textarea);
        textarea.select();
        try {
            document.execCommand('copy');
            showMTPLToast('Copied to clipboard!', 'success', 2000);
        } catch (err) {
            showMTPLToast('Failed to copy to clipboard', 'error');
        }
        document.body.removeChild(textarea);
    }
}

// Download as CSV
function mtplDownloadCSV(data, filename = 'export.csv') {
    const csv = data.map(row => row.map(cell => `"${cell}"`).join(',')).join('\n');
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    const url = URL.createObjectURL(blob);
    link.setAttribute('href', url);
    link.setAttribute('download', filename);
    link.style.visibility = 'hidden';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}

// ============================================
// 7. INITIALIZATION
// ============================================

document.addEventListener('DOMContentLoaded', function() {
    // Convert flash messages to toasts
    const flashMessages = document.querySelectorAll('.mtpl-flash-message');
    flashMessages.forEach(msg => {
        const message = msg.getAttribute('data-message');
        const type = msg.getAttribute('data-type');
        showMTPLToast(message, type);
        msg.remove();
    });
    
    // Initialize all tables with .mtpl-table-auto class
    document.querySelectorAll('.mtpl-table-auto').forEach(table => {
        new MTPLTable(table.id, {
            sortable: true,
            filterable: true,
            paginate: true
        });
    });
    
    // Fix for modal backdrop blocking clicks
    cleanupModalBackdrops();
});

// ============================================
// 9. MODAL BACKDROP CLEANUP - OPTIMIZED
// ============================================

function cleanupModalBackdrops() {
    // Quick check - only run if there are actually backdrop elements
    const backdrops = document.querySelectorAll('.mtpl-modal-backdrop:not(.show), .modal-backdrop:not(.show)');
    
    if (backdrops.length === 0) return; // Exit early if nothing to clean
    
    backdrops.forEach(backdrop => {
        backdrop.style.display = 'none';
        backdrop.style.pointerEvents = 'none';
        backdrop.style.zIndex = '-9999';
        backdrop.style.visibility = 'hidden';
    });
    
    // Ensure body is reset if no modals are open
    const openModals = document.querySelectorAll('.mtpl-modal-backdrop.show, .modal.show');
    if (openModals.length === 0) {
        document.body.style.overflow = '';
        document.body.style.pointerEvents = 'auto';
        document.body.classList.remove('modal-open');
    }
}

// Run cleanup on page load ONCE
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', cleanupModalBackdrops);
} else {
    cleanupModalBackdrops();
}

// REMOVED: Periodic cleanup that was causing performance issues
// Only run cleanup when needed, not on a timer

// ============================================
// 8. CONFIRM DIALOG
// ============================================

function showConfirmDialog(message, onConfirm, onCancel = null) {
    openMTPLModal({
        title: 'Confirm Action',
        body: `<p>${message}</p>`,
        size: 'small',
        buttons: [
            {
                text: 'Cancel',
                class: 'secondary',
                onclick: () => {
                    closeMTPLModal();
                    if (onCancel) onCancel();
                }
            },
            {
                text: 'Confirm',
                class: 'danger',
                onclick: () => {
                    closeMTPLModal();
                    if (onConfirm) onConfirm();
                }
            }
        ]
    });
}

// Add fadeOut animation
const style = document.createElement('style');
style.textContent = `
    @keyframes mtpl-fadeOut {
        from { opacity: 1; }
        to { opacity: 0; }
    }
`;
document.head.appendChild(style);

