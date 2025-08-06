/**
 * Export Scheduling Manager JavaScript
 * 
 * Handles the frontend interface for advanced export scheduling
 * including creating, managing, and monitoring scheduled exports.
 */

class ExportSchedulingManager {
    constructor() {
        this.apiBase = '/api/data-export';
        this.scheduledExports = [];
        this.exportTemplates = {};
        this.currentEditId = null;
        this.schedulerRunning = false;
        this.deliveryChannelCount = 0;
        
        this.init();
    }

    async init() {
        try {
            await this.loadScheduledExports();
            await this.loadExportTemplates();
            await this.loadSchedulerStatus();
            
            this.renderScheduledExports();
            this.renderExportTemplates();
            this.updateSchedulerStatus();
            
            // Start periodic updates
            setInterval(() => {
                this.loadScheduledExports();
                this.loadSchedulerStatus();
            }, 30000); // Update every 30 seconds
            
        } catch (error) {
            console.error('Failed to initialize export scheduling manager:', error);
            this.showAlert('Failed to load scheduling interface. Please refresh the page.', 'error');
        }
    }

    async loadScheduledExports() {
        try {
            const response = await fetch(`${this.apiBase}/schedule/advanced`);
            if (response.ok) {
                const data = await response.json();
                this.scheduledExports = data.scheduled_exports || [];
            } else {
                throw new Error('Failed to load scheduled exports');
            }
        } catch (error) {
            console.error('Error loading scheduled exports:', error);
        }
    }

    async loadExportTemplates() {
        try {
            const response = await fetch(`${this.apiBase}/schedule/templates`);
            if (response.ok) {
                const data = await response.json();
                this.exportTemplates = data.templates || {};
            } else {
                console.warn('No export templates available');
            }
        } catch (error) {
            console.error('Error loading export templates:', error);
        }
    }

    async loadSchedulerStatus() {
        try {
            const response = await fetch(`${this.apiBase}/schedule/status`);
            if (response.ok) {
                const status = await response.json();
                this.schedulerRunning = status.scheduler_running;
                this.schedulerStats = status;
            } else {
                throw new Error('Failed to load scheduler status');
            }
        } catch (error) {
            console.error('Error loading scheduler status:', error);
        }
    }

    renderScheduledExports() {
        const container = document.getElementById('scheduleList');
        
        if (this.scheduledExports.length === 0) {
            container.innerHTML = `
                <div style="padding: 60px; text-align: center; color: #6c757d;">
                    <i class="fas fa-calendar-plus" style="font-size: 48px; margin-bottom: 20px; opacity: 0.5;"></i>
                    <h3>No Scheduled Exports</h3>
                    <p>Create your first automated export schedule to get started.</p>
                    <button class="btn btn-primary" onclick="showCreateModal()">
                        <i class="fas fa-plus"></i> Create First Schedule
                    </button>
                </div>
            `;
            return;
        }

        container.innerHTML = this.scheduledExports.map(schedule => {
            const nextRun = schedule.next_run ? new Date(schedule.next_run).toLocaleString() : 'Not scheduled';
            const lastRun = schedule.last_run ? new Date(schedule.last_run).toLocaleString() : 'Never';
            
            return `
                <div class="schedule-item">
                    <div class="schedule-info">
                        <div class="schedule-name">${schedule.name}</div>
                        <div class="schedule-details">
                            <strong>Schedule:</strong> ${schedule.schedule} | 
                            <strong>Next Run:</strong> ${nextRun} | 
                            <strong>Last Run:</strong> ${lastRun}
                        </div>
                        <div class="schedule-status">
                            <span class="status-badge ${schedule.status === 'active' ? 'status-active' : 'status-disabled'}">
                                ${schedule.status}
                            </span>
                            <span style="font-size: 12px; color: #6c757d;">
                                ${schedule.run_count} runs | ${schedule.failure_count} failures | ${schedule.delivery_channels} channels
                            </span>
                        </div>
                    </div>
                    <div class="schedule-actions">
                        <button class="btn btn-secondary btn-small" onclick="editSchedule('${schedule.export_id}')">
                            <i class="fas fa-edit"></i> Edit
                        </button>
                        <button class="btn btn-warning btn-small" onclick="toggleSchedule('${schedule.export_id}', '${schedule.status}')">
                            <i class="fas fa-${schedule.status === 'active' ? 'pause' : 'play'}"></i>
                            ${schedule.status === 'active' ? 'Disable' : 'Enable'}
                        </button>
                        <button class="btn btn-danger btn-small" onclick="deleteSchedule('${schedule.export_id}')">
                            <i class="fas fa-trash"></i> Delete
                        </button>
                    </div>
                </div>
            `;
        }).join('');
    }

    renderExportTemplates() {
        const container = document.getElementById('templateGrid');
        
        const templates = Object.entries(this.exportTemplates);
        
        if (templates.length === 0) {
            container.innerHTML = '<p style="color: #6c757d;">No templates available</p>';
            return;
        }

        container.innerHTML = templates.map(([key, template]) => `
            <div class="template-card" onclick="selectTemplate('${key}')">
                <div class="template-name">${template.name}</div>
                <div class="template-description">${template.description}</div>
            </div>
        `).join('');
    }

    updateSchedulerStatus() {
        const statusElement = document.getElementById('schedulerRunning');
        const toggleBtn = document.getElementById('toggleSchedulerBtn');
        
        if (this.schedulerRunning) {
            statusElement.textContent = '▶️';
            statusElement.parentElement.querySelector('.stat-label').textContent = 'Running';
            toggleBtn.textContent = 'Stop Scheduler';
            toggleBtn.className = 'btn btn-danger btn-small';
        } else {
            statusElement.textContent = '⏸️';
            statusElement.parentElement.querySelector('.stat-label').textContent = 'Stopped';
            toggleBtn.textContent = 'Start Scheduler';
            toggleBtn.className = 'btn btn-success btn-small';
        }

        // Update statistics
        if (this.schedulerStats) {
            document.getElementById('totalSchedules').textContent = this.schedulerStats.total_schedules || 0;
            document.getElementById('activeSchedules').textContent = this.schedulerStats.active_schedules || 0;
            document.getElementById('totalRuns').textContent = this.schedulerStats.total_runs || 0;
            document.getElementById('successRate').textContent = `${this.schedulerStats.success_rate?.toFixed(1) || 0}%`;
        }
    }

    showCreateModal() {
        document.getElementById('modalTitle').textContent = 'Create Scheduled Export';
        document.getElementById('scheduleForm').reset();
        this.currentEditId = null;
        this.deliveryChannelCount = 0;
        
        // Clear delivery channels
        document.getElementById('deliveryChannels').innerHTML = '';
        
        // Add default email channel
        this.addDeliveryChannel('email');
        
        document.getElementById('scheduleModal').style.display = 'block';
        this.updateScheduleExample();
    }

    closeModal() {
        document.getElementById('scheduleModal').style.display = 'none';
    }

    selectTemplate(templateKey) {
        // Remove previous selection
        document.querySelectorAll('.template-card').forEach(card => {
            card.classList.remove('selected');
        });
        
        // Select current template
        event.currentTarget.classList.add('selected');
        
        // Apply template configuration
        const template = this.exportTemplates[templateKey];
        if (template && template.export_config) {
            const config = template.export_config;
            
            if (config.data_source) {
                document.getElementById('exportDataSource').value = config.data_source;
            }
            if (config.format) {
                document.getElementById('exportFormat').value = config.format;
            }
            if (config.filters && config.filters.date_range) {
                document.getElementById('dateRange').value = config.filters.date_range;
            }
            
            // Update name if not already set
            if (!document.getElementById('scheduleName').value) {
                document.getElementById('scheduleName').value = template.name;
            }
        }
    }

    updateScheduleExample() {
        const pattern = document.getElementById('schedulePattern').value;
        const customGroup = document.getElementById('customPatternGroup');
        const previewElement = document.getElementById('nextRunPreview');
        
        if (pattern === 'custom') {
            customGroup.style.display = 'block';
            previewElement.value = 'Enter custom pattern to see preview';
        } else {
            customGroup.style.display = 'none';
            
            // Calculate next run time (simplified)
            const now = new Date();
            let nextRun = new Date(now);
            
            if (pattern.includes('daily')) {
                nextRun.setDate(nextRun.getDate() + 1);
            } else if (pattern.includes('weekly')) {
                nextRun.setDate(nextRun.getDate() + 7);
            } else if (pattern.includes('monthly')) {
                nextRun.setMonth(nextRun.getMonth() + 1);
            } else if (pattern.includes('weekdays')) {
                // Next weekday
                do {
                    nextRun.setDate(nextRun.getDate() + 1);
                } while (nextRun.getDay() === 0 || nextRun.getDay() === 6);
            }
            
            // Set time if specified
            const timeMatch = pattern.match(/at (\d{2}):(\d{2})/);
            if (timeMatch) {
                nextRun.setHours(parseInt(timeMatch[1]), parseInt(timeMatch[2]), 0, 0);
            }
            
            previewElement.value = nextRun.toLocaleString();
        }
    }

    addDeliveryChannel(type = 'email') {
        const container = document.getElementById('deliveryChannels');
        const channelId = `channel_${++this.deliveryChannelCount}`;
        
        const channelHtml = `
            <div class="channel-item" id="${channelId}">
                <div class="channel-header">
                    <select class="channel-type" onchange="updateChannelType('${channelId}', this.value)">
                        <option value="email" ${type === 'email' ? 'selected' : ''}>Email</option>
                        <option value="ftp" ${type === 'ftp' ? 'selected' : ''}>FTP</option>
                        <option value="s3" ${type === 's3' ? 'selected' : ''}>Amazon S3</option>
                    </select>
                    <button type="button" class="btn btn-danger btn-small" onclick="removeDeliveryChannel('${channelId}')">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
                <div class="channel-config" id="${channelId}_config">
                    ${this.getChannelConfigHtml(type, channelId)}
                </div>
            </div>
        `;
        
        container.insertAdjacentHTML('beforeend', channelHtml);
    }

    getChannelConfigHtml(type, channelId) {
        switch (type) {
            case 'email':
                return `
                    <div class="form-row">
                        <div class="form-group">
                            <label>SMTP Server</label>
                            <input type="text" class="form-control" name="smtp_server" placeholder="smtp.gmail.com" required>
                        </div>
                        <div class="form-group">
                            <label>Port</label>
                            <input type="number" class="form-control" name="smtp_port" value="587" required>
                        </div>
                    </div>
                    <div class="form-row">
                        <div class="form-group">
                            <label>Username</label>
                            <input type="text" class="form-control" name="username" placeholder="user@example.com" required>
                        </div>
                        <div class="form-group">
                            <label>Password</label>
                            <input type="password" class="form-control" name="password" required>
                        </div>
                    </div>
                    <div class="form-group">
                        <label>Recipients (comma-separated)</label>
                        <input type="text" class="form-control" name="recipients" placeholder="admin@company.com, manager@company.com" required>
                    </div>
                    <div class="form-group">
                        <label>
                            <input type="checkbox" name="use_tls" checked> Use TLS
                        </label>
                    </div>
                `;
            
            case 'ftp':
                return `
                    <div class="form-row">
                        <div class="form-group">
                            <label>FTP Server</label>
                            <input type="text" class="form-control" name="server" placeholder="ftp.example.com" required>
                        </div>
                        <div class="form-group">
                            <label>Remote Path</label>
                            <input type="text" class="form-control" name="remote_path" placeholder="/exports/" required>
                        </div>
                    </div>
                    <div class="form-row">
                        <div class="form-group">
                            <label>Username</label>
                            <input type="text" class="form-control" name="username" required>
                        </div>
                        <div class="form-group">
                            <label>Password</label>
                            <input type="password" class="form-control" name="password" required>
                        </div>
                    </div>
                `;
            
            case 's3':
                return `
                    <div class="form-row">
                        <div class="form-group">
                            <label>AWS Access Key</label>
                            <input type="text" class="form-control" name="aws_access_key" required>
                        </div>
                        <div class="form-group">
                            <label>AWS Secret Key</label>
                            <input type="password" class="form-control" name="aws_secret_key" required>
                        </div>
                    </div>
                    <div class="form-row">
                        <div class="form-group">
                            <label>Bucket Name</label>
                            <input type="text" class="form-control" name="bucket_name" required>
                        </div>
                        <div class="form-group">
                            <label>Region</label>
                            <input type="text" class="form-control" name="region" value="us-east-1" required>
                        </div>
                    </div>
                    <div class="form-group">
                        <label>Key Prefix</label>
                        <input type="text" class="form-control" name="prefix" placeholder="exports/">
                    </div>
                `;
            
            default:
                return '<p>Unknown channel type</p>';
        }
    }

    updateChannelType(channelId, type) {
        const configContainer = document.getElementById(`${channelId}_config`);
        configContainer.innerHTML = this.getChannelConfigHtml(type, channelId);
    }

    removeDeliveryChannel(channelId) {
        const element = document.getElementById(channelId);
        if (element) {
            element.remove();
        }
    }

    async submitScheduleForm(event) {
        event.preventDefault();
        
        try {
            // Collect form data
            const formData = {
                name: document.getElementById('scheduleName').value,
                description: document.getElementById('scheduleDescription').value,
                schedule: document.getElementById('schedulePattern').value === 'custom' 
                    ? document.getElementById('customPattern').value 
                    : document.getElementById('schedulePattern').value,
                export_config: {
                    data_source: document.getElementById('exportDataSource').value,
                    customization: {
                        format: document.getElementById('exportFormat').value,
                        include_headers: true,
                        include_metadata: true
                    },
                    filters: {
                        date_range: document.getElementById('dateRange').value
                    }
                },
                delivery_channels: this.collectDeliveryChannels(),
                enabled: true
            };
            
            // Validate delivery channels
            if (formData.delivery_channels.length === 0) {
                throw new Error('At least one delivery channel is required');
            }
            
            let response;
            if (this.currentEditId) {
                // Update existing schedule
                response = await fetch(`${this.apiBase}/schedule/advanced/${this.currentEditId}`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(formData)
                });
            } else {
                // Create new schedule
                response = await fetch(`${this.apiBase}/schedule/advanced`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(formData)
                });
            }
            
            if (response.ok) {
                this.showAlert(`Schedule ${this.currentEditId ? 'updated' : 'created'} successfully!`, 'success');
                this.closeModal();
                await this.loadScheduledExports();
                this.renderScheduledExports();
            } else {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Failed to save schedule');
            }
            
        } catch (error) {
            console.error('Error saving schedule:', error);
            this.showAlert(`Failed to save schedule: ${error.message}`, 'error');
        }
    }

    collectDeliveryChannels() {
        const channels = [];
        const channelElements = document.querySelectorAll('.channel-item');
        
        channelElements.forEach((element, index) => {
            const typeSelect = element.querySelector('.channel-type');
            const type = typeSelect.value;
            const config = { type, name: `${type}_channel_${index + 1}`, enabled: true };
            
            // Collect configuration fields
            const inputs = element.querySelectorAll('input, select');
            inputs.forEach(input => {
                if (input.name && input.name !== 'type') {
                    if (input.type === 'checkbox') {
                        config[input.name] = input.checked;
                    } else if (input.name === 'recipients') {
                        config[input.name] = input.value.split(',').map(email => email.trim()).filter(email => email);
                    } else {
                        config[input.name] = input.value;
                    }
                }
            });
            
            channels.push(config);
        });
        
        return channels;
    }

    async editSchedule(exportId) {
        try {
            const response = await fetch(`${this.apiBase}/schedule/advanced/${exportId}`);
            if (response.ok) {
                const schedule = await response.json();
                this.populateEditForm(schedule);
                this.currentEditId = exportId;
                document.getElementById('modalTitle').textContent = 'Edit Scheduled Export';
                document.getElementById('scheduleModal').style.display = 'block';
            } else {
                throw new Error('Failed to load schedule details');
            }
        } catch (error) {
            console.error('Error loading schedule for edit:', error);
            this.showAlert('Failed to load schedule details', 'error');
        }
    }

    populateEditForm(schedule) {
        document.getElementById('scheduleName').value = schedule.name || '';
        document.getElementById('scheduleDescription').value = schedule.description || '';
        
        // Set schedule pattern
        const schedulePattern = schedule.schedule;
        const patternSelect = document.getElementById('schedulePattern');
        if ([...patternSelect.options].some(opt => opt.value === schedulePattern)) {
            patternSelect.value = schedulePattern;
        } else {
            patternSelect.value = 'custom';
            document.getElementById('customPattern').value = schedulePattern;
        }
        
        this.updateScheduleExample();
        
        // Set export configuration (would need more detailed implementation)
        // This is simplified for the demo
    }

    async toggleSchedule(exportId, currentStatus) {
        try {
            const newStatus = currentStatus === 'active' ? 'disabled' : 'active';
            const response = await fetch(`${this.apiBase}/schedule/advanced/${exportId}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ enabled: newStatus === 'active' })
            });
            
            if (response.ok) {
                this.showAlert(`Schedule ${newStatus === 'active' ? 'enabled' : 'disabled'} successfully`, 'success');
                await this.loadScheduledExports();
                this.renderScheduledExports();
            } else {
                throw new Error('Failed to toggle schedule');
            }
        } catch (error) {
            console.error('Error toggling schedule:', error);
            this.showAlert('Failed to toggle schedule', 'error');
        }
    }

    async deleteSchedule(exportId) {
        if (!confirm('Are you sure you want to delete this scheduled export?')) {
            return;
        }
        
        try {
            const response = await fetch(`${this.apiBase}/schedule/advanced/${exportId}`, {
                method: 'DELETE'
            });
            
            if (response.ok) {
                this.showAlert('Schedule deleted successfully', 'success');
                await this.loadScheduledExports();
                this.renderScheduledExports();
            } else {
                throw new Error('Failed to delete schedule');
            }
        } catch (error) {
            console.error('Error deleting schedule:', error);
            this.showAlert('Failed to delete schedule', 'error');
        }
    }

    async toggleScheduler() {
        try {
            const endpoint = this.schedulerRunning ? '/schedule/stop' : '/schedule/start';
            const response = await fetch(`${this.apiBase}${endpoint}`, { method: 'POST' });
            
            if (response.ok) {
                this.schedulerRunning = !this.schedulerRunning;
                this.updateSchedulerStatus();
                this.showAlert(`Scheduler ${this.schedulerRunning ? 'started' : 'stopped'} successfully`, 'success');
            } else {
                throw new Error('Failed to toggle scheduler');
            }
        } catch (error) {
            console.error('Error toggling scheduler:', error);
            this.showAlert('Failed to toggle scheduler', 'error');
        }
    }

    showAlert(message, type = 'info') {
        const alertClass = `alert-${type === 'info' ? 'success' : type}`;
        const alertHtml = `
            <div class="alert ${alertClass}" style="position: fixed; top: 20px; right: 20px; z-index: 1001; max-width: 400px;">
                ${message}
                <button onclick="this.parentElement.remove()" style="float: right; background: none; border: none; font-size: 16px; cursor: pointer;">×</button>
            </div>
        `;
        
        document.body.insertAdjacentHTML('afterbegin', alertHtml);
        
        // Auto-remove after 5 seconds
        setTimeout(() => {
            const alert = document.querySelector('.alert[style*="position: fixed"]');
            if (alert) alert.remove();
        }, 5000);
    }
}

// Global functions for HTML onclick handlers
function showCreateModal() {
    exportSchedulingManager.showCreateModal();
}

function closeModal() {
    exportSchedulingManager.closeModal();
}

function selectTemplate(templateKey) {
    exportSchedulingManager.selectTemplate(templateKey);
}

function updateScheduleExample() {
    exportSchedulingManager.updateScheduleExample();
}

function addDeliveryChannel() {
    exportSchedulingManager.addDeliveryChannel();
}

function updateChannelType(channelId, type) {
    exportSchedulingManager.updateChannelType(channelId, type);
}

function removeDeliveryChannel(channelId) {
    exportSchedulingManager.removeDeliveryChannel(channelId);
}

function editSchedule(exportId) {
    exportSchedulingManager.editSchedule(exportId);
}

function toggleSchedule(exportId, status) {
    exportSchedulingManager.toggleSchedule(exportId, status);
}

function deleteSchedule(exportId) {
    exportSchedulingManager.deleteSchedule(exportId);
}

function toggleScheduler() {
    exportSchedulingManager.toggleScheduler();
}

// Initialize the export scheduling manager when the page loads
let exportSchedulingManager;
document.addEventListener('DOMContentLoaded', () => {
    exportSchedulingManager = new ExportSchedulingManager();
    
    // Add form submit handler
    document.getElementById('scheduleForm').addEventListener('submit', (event) => {
        exportSchedulingManager.submitScheduleForm(event);
    });
    
    // Handle custom pattern changes
    document.getElementById('customPattern').addEventListener('input', updateScheduleExample);
    
    // Close modal when clicking outside
    window.addEventListener('click', (event) => {
        const modal = document.getElementById('scheduleModal');
        if (event.target === modal) {
            closeModal();
        }
    });
});