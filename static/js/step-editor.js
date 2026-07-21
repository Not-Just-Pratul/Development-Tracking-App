/**
 * Step Inline Editing Module
 * Enables inline editing of step names, dates, and status
 */

class StepEditor {
    constructor() {
        this.editingStepId = null;
        this.initEventListeners();
    }

    initEventListeners() {
        document.addEventListener('DOMContentLoaded', () => {
            this.attachEditListeners();
        });
    }

    attachEditListeners() {
        // Edit step name inline
        document.querySelectorAll('.edit-step-name').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.preventDefault();
                const stepId = btn.dataset.stepId;
                this.editStepName(stepId);
            });
        });

        // Edit step dates inline
        document.querySelectorAll('.edit-step-dates').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.preventDefault();
                const stepId = btn.dataset.stepId;
                this.editStepDates(stepId);
            });
        });

        // Quick status change
        document.querySelectorAll('.quick-status-change').forEach(badge => {
            badge.addEventListener('click', (e) => {
                const stepId = badge.dataset.stepId;
                const currentStatus = badge.dataset.status;
                this.showStatusModal(stepId, currentStatus);
            });
        });

        // Edit stage name inline
        document.querySelectorAll('.edit-stage-name').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                const stageId = btn.dataset.stageId;
                this.editStageName(stageId);
            });
        });
    }

    editStepName(stepId) {
        const nameCell = document.querySelector(`#step-name-${stepId}`);
        const currentName = nameCell.textContent.trim();
        
        // Create inline edit form
        const form = document.createElement('form');
        form.className = 'inline-edit-form d-flex gap-2';
        form.innerHTML = `
            <input type="text" class="form-control form-control-sm" 
                   value="${this.escapeHtml(currentName)}" 
                   name="name" required autofocus>
            <button type="submit" class="btn btn-sm btn-success">
                <i class="bi bi-check"></i>
            </button>
            <button type="button" class="btn btn-sm btn-secondary cancel-edit">
                <i class="bi bi-x"></i>
            </button>
        `;

        // Handle form submission
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            const newName = form.querySelector('input').value.trim();
            if (newName) {
                await this.updateStepField(stepId, 'name', newName);
                nameCell.innerHTML = `<strong>${this.escapeHtml(newName)}</strong>`;
                form.remove();
            }
        });

        // Handle cancel
        form.querySelector('.cancel-edit').addEventListener('click', () => {
            form.remove();
        });

        // Insert form and hide original content
        nameCell.appendChild(form);
        form.querySelector('input').focus();
        form.querySelector('input').select();
    }

    editStageName(stageId) {
        const nameSpan = document.querySelector(`#stage-name-${stageId}`);
        const stageLabel = nameSpan.querySelector('strong');
        const currentName = stageLabel.textContent.replace('Stage:', '').trim();
        
        // Create inline edit form
        const form = document.createElement('form');
        form.className = 'inline-edit-form d-flex gap-2 mt-2';
        form.innerHTML = `
            <input type="text" class="form-control form-control-sm" 
                   value="${this.escapeHtml(currentName)}" 
                   name="name" required autofocus>
            <button type="submit" class="btn btn-sm btn-success">
                <i class="bi bi-check"></i>
            </button>
            <button type="button" class="btn btn-sm btn-secondary cancel-edit">
                <i class="bi bi-x"></i>
            </button>
        `;

        // Handle form submission
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            const newName = form.querySelector('input').value.trim();
            if (newName) {
                await this.updateStageName(stageId, newName);
                location.reload(); // Reload to update stage name everywhere
            }
        });

        // Handle cancel
        form.querySelector('.cancel-edit').addEventListener('click', () => {
            form.remove();
        });

        // Insert form after the stage name
        nameSpan.appendChild(form);
        form.querySelector('input').focus();
        form.querySelector('input').select();
    }

    editStepDates(stepId) {
        const row = document.querySelector(`#step-row-${stepId}`);
        const startDate = row.dataset.startDate || '';
        const estimatedDate = row.dataset.estimatedDate || '';

        // Show modal with date editors
        const modal = this.createDateEditModal(stepId, startDate, estimatedDate);
        document.body.appendChild(modal);
        const bsModal = new bootstrap.Modal(modal);
        bsModal.show();

        modal.addEventListener('hidden.bs.modal', () => {
            modal.remove();
        });
    }

    createDateEditModal(stepId, startDate, estimatedDate) {
        const modal = document.createElement('div');
        modal.className = 'modal fade';
        modal.innerHTML = `
            <div class="modal-dialog">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">Edit Step Dates</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <form id="date-edit-form">
                        <div class="modal-body">
                            <div class="mb-3">
                                <label class="form-label">Start Date</label>
                                <input type="date" class="form-control" name="start_date" 
                                       value="${startDate}">
                            </div>
                            <div class="mb-3">
                                <label class="form-label">Estimated Completion</label>
                                <input type="date" class="form-control" name="expected_end_date" 
                                       value="${estimatedDate}">
                            </div>
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                            <button type="submit" class="btn btn-primary">Save Changes</button>
                        </div>
                    </form>
                </div>
            </div>
        `;

        modal.querySelector('form').addEventListener('submit', async (e) => {
            e.preventDefault();
            const formData = new FormData(e.target);
            await this.updateStepDates(stepId, formData);
            bootstrap.Modal.getInstance(modal).hide();
            location.reload(); // Refresh to show updated dates
        });

        return modal;
    }

    showStatusModal(stepId, currentStatus) {
        const modal = document.createElement('div');
        modal.className = 'modal fade';
        modal.innerHTML = `
            <div class="modal-dialog modal-sm">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">Change Status</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        <div class="d-grid gap-2">
                            <button class="btn btn-outline-secondary status-option" data-status="pending">
                                <i class="bi bi-circle"></i> Pending
                            </button>
                            <button class="btn btn-outline-primary status-option" data-status="in_progress">
                                <i class="bi bi-arrow-clockwise"></i> In Progress
                            </button>
                            <button class="btn btn-outline-success status-option" data-status="completed">
                                <i class="bi bi-check-circle"></i> Completed
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;

        document.body.appendChild(modal);
        const bsModal = new bootstrap.Modal(modal);
        bsModal.show();

        modal.querySelectorAll('.status-option').forEach(btn => {
            btn.addEventListener('click', async () => {
                const newStatus = btn.dataset.status;
                await this.updateStepStatus(stepId, newStatus);
                bsModal.hide();
                location.reload();
            });
        });

        modal.addEventListener('hidden.bs.modal', () => {
            modal.remove();
        });
    }

    async updateStepField(stepId, field, value) {
        const formData = new FormData();
        formData.append(field, value);
        
        try {
            const response = await fetch(`/ui/steps/${stepId}/update`, {
                method: 'POST',
                body: formData
            });
            
            if (!response.ok) {
                throw new Error('Update failed');
            }
            
            this.showToast('Step updated successfully', 'success');
        } catch (error) {
            this.showToast('Failed to update step', 'error');
            console.error('Update error:', error);
        }
    }

    async updateStepDates(stepId, formData) {
        try {
            const response = await fetch(`/ui/steps/${stepId}/update`, {
                method: 'POST',
                body: formData
            });
            
            if (!response.ok) {
                throw new Error('Update failed');
            }
            
            this.showToast('Dates updated successfully', 'success');
        } catch (error) {
            this.showToast('Failed to update dates', 'error');
            console.error('Update error:', error);
        }
    }

    async updateStepStatus(stepId, status) {
        const formData = new FormData();
        formData.append('status', status);
        
        try {
            const response = await fetch(`/ui/steps/${stepId}/status`, {
                method: 'POST',
                body: formData
            });
            
            if (!response.ok) {
                throw new Error('Status update failed');
            }
            
            this.showToast('Status updated successfully', 'success');
        } catch (error) {
            this.showToast('Failed to update status', 'error');
            console.error('Status update error:', error);
        }
    }

    async updateStageName(stageId, name) {
        const formData = new FormData();
        formData.append('name', name);
        
        try {
            const response = await fetch(`/ui/stages/${stageId}/update-name`, {
                method: 'POST',
                body: formData
            });
            
            if (!response.ok) {
                throw new Error('Stage name update failed');
            }
            
            this.showToast('Stage name updated successfully', 'success');
        } catch (error) {
            this.showToast('Failed to update stage name', 'error');
            console.error('Stage name update error:', error);
        }
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    showToast(message, type = 'info') {
        // Create toast notification
        const toast = document.createElement('div');
        toast.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
        toast.style.cssText = 'top: 20px; right: 20px; z-index: 10500; min-width: 250px;';
        toast.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        document.body.appendChild(toast);
        
        setTimeout(() => {
            toast.remove();
        }, 3000);
    }
}

// Initialize step editor
const stepEditor = new StepEditor();

// Export for use in other scripts (browser-compatible)
window.StepEditor = StepEditor;
