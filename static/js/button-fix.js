(function() {
    'use strict';
    
    // Fix 1: Remove blocking modal backdrops (only hidden ones)
    function removeBlockingBackdrops() {
        const backdrops = document.querySelectorAll('.mtpl-modal-backdrop, .modal-backdrop, .master-modal-backdrop');
        backdrops.forEach(backdrop => {
            // Only hide backdrops that are not currently showing a modal
            if (!backdrop.classList.contains('show') && backdrop.style.display !== 'flex') {
                backdrop.style.cssText = 'display: none !important; pointer-events: none !important; z-index: -9999 !important; visibility: hidden !important;';
            }
        });
        
        // Ensure body is clickable only if no modals are open
        const openModals = document.querySelectorAll('.modal.show, .mtpl-modal-backdrop.show, .master-modal.modal-open');
        if (openModals.length === 0) {
            document.body.style.overflow = '';
            document.body.style.pointerEvents = 'auto';
            document.body.classList.remove('modal-open');
        }
    }
    
    // Fix 2: Ensure main content is clickable (but don't interfere with modals)
    function ensureMainClickable() {
        // Only fix if no modals are open
        const openModals = document.querySelectorAll('.modal.show, .mtpl-modal-backdrop.show, .master-modal.modal-open');
        if (openModals.length > 0) {
            return; // Don't interfere with open modals
        }
        
        const main = document.querySelector('main');
        if (main) {
            main.style.pointerEvents = 'auto';
        }
        
        // Ensure all buttons are clickable
        const buttons = document.querySelectorAll('button:not([disabled]), .btn:not([disabled]), a.btn:not([disabled])');
        buttons.forEach(btn => {
            btn.style.pointerEvents = 'auto';
        });
    }
    
    // Fix 3: Override modal close to properly cleanup
    const originalCloseMasterModal = window.closeMasterModal;
    if (originalCloseMasterModal) {
        window.closeMasterModal = function() {
            originalCloseMasterModal();
            // Force cleanup after modal closes
            setTimeout(() => {
                removeBlockingBackdrops();
                ensureMainClickable();
            }, 150);
        };
    }
    
    const originalCloseMTPLModal = window.closeMTPLModal;
    if (originalCloseMTPLModal) {
        window.closeMTPLModal = function() {
            originalCloseMTPLModal();
            // Force cleanup after modal closes
            setTimeout(() => {
                removeBlockingBackdrops();
                ensureMainClickable();
            }, 150);
        };
    }
    
    // Fix 4: Run cleanup on page load
    function init() {
        removeBlockingBackdrops();
        ensureMainClickable();
    }
    
    // Run immediately if DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
    
    // Fix 5: Run cleanup only when explicitly needed (on page visibility change)
    document.addEventListener('visibilitychange', () => {
        if (!document.hidden) {
            // Page became visible, cleanup any stale backdrops
            setTimeout(() => {
                removeBlockingBackdrops();
                ensureMainClickable();
            }, 300);
        }
    });
})();
