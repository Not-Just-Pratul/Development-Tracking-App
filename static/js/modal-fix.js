/**
 * Modal Fix for Empty Class Token Error
 * Fixes: "Failed to execute 'add' on 'DOMTokenList': The token provided must not be empty"
 */

(function() {
    'use strict';
    
    // Override the openMasterModal function to fix empty class issue
    const originalOpenMasterModal = window.openMasterModal;
    
    if (originalOpenMasterModal) {
        window.openMasterModal = function(titleOrOptions, bodyHTML, buttons = []) {
            // Support both object format and individual parameters
            let title, body, modalButtons, size;
            
            if (typeof titleOrOptions === 'object' && titleOrOptions !== null) {
                // Object format: {title, body, buttons, size}
                title = titleOrOptions.title;
                body = titleOrOptions.body;
                modalButtons = titleOrOptions.buttons || [];
                size = titleOrOptions.size || 'medium'; // Default to medium if not specified
            } else {
                // Individual parameters format
                title = titleOrOptions;
                body = bodyHTML;
                modalButtons = buttons;
                size = 'medium'; // Default size
            }
            
            // Ensure size is valid
            if (!size || size === '') {
                size = 'medium';
            }
            
            // Call original with fixed parameters
            return originalOpenMasterModal.call(this, {
                title: title,
                body: body,
                buttons: modalButtons,
                size: size
            });
        };
    }
    
    // Also patch classList.add to prevent empty tokens
    const originalAdd = DOMTokenList.prototype.add;
    DOMTokenList.prototype.add = function(...tokens) {
        // Filter out empty tokens
        const validTokens = tokens.filter(token => token && token.trim() !== '');
        if (validTokens.length > 0) {
            return originalAdd.apply(this, validTokens);
        }
    };
})();
