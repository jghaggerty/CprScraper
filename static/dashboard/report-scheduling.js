/**
 * Report Scheduling JavaScript
 * 
 * Handles the frontend functionality for report scheduling and automated delivery.
 */

class ReportScheduler {
    constructor() {
        this.apiBase = '/api/reports/scheduling';
        this.schedules = [];
        this.currentTab = 'schedules';
        
        this.init();
    }
    
    init() {
        this.loadSchedules();
        this.setupEventListeners();
        this.loadScheduleOptions();
    }
    
    setupEventListeners() {
        // Schedule form submission
        const scheduleForm = document.getElementById('schedule-form');
        if (scheduleForm) {
            scheduleForm.addEventListener('submit', (e) => this.handleCreateSchedule(e));
        }
    }
    
    async loadSchedules() {
        try {
            const response = await fetch(`${this.apiBase}/schedules`, {
                headers: {
                    'Authorization': `Bearer ${localStorage.getItem('token')}`
                }
            });
            
            if (!response.ok) {
                throw new Error(`Failed to load schedules: ${response.statusText}`);
            }
            
            this.schedules = await response.json();
            this.renderSchedules();
            
        } catch (error) {
            console.error('Failed to load schedules:', error);
            this.showError(`Failed to load schedules: ${error.message}`);
        }
    }
    
    renderSchedules() {
        const container = document.getElementById('schedules-list');
        if (!container) return;
        
        if (this.schedules.length === 0) {
            container.innerHTML = '<p>No schedules found. Create your first schedule to get started.</p>';
            return;
        }
        
        container.innerHTML = this.schedules.map(schedule => this.renderScheduleCard(schedule)).join('');
    }
    
    renderScheduleCard(schedule) {
        const statusClass = schedule.is_active ? 'status-active' : 'status-inactive';
        const statusText = schedule.is_active ? 'Active' : 'Inactive';
        
        const nextRun = schedule.next_run ? new Date(schedule.next_run).toLocaleString() : 'Not scheduled';
        const lastRun = schedule.last_run ? new Date(schedule.last_run).toLocaleString() : 'Never';
        
        return `
            <div class="schedule-card">
                <h3>${schedule.name}</h3>
                <span class="schedule-status ${statusClass}">${statusText}</span>
                
                ${schedule.description ? `<p>${schedule.description}</p>` : ''}
                
                <div class="schedule-details">
                    <p><strong>Type:</strong> ${this.formatScheduleType(schedule.schedule_type)}</p>
                    <p><strong>Timezone:</strong> ${schedule.timezone}</p>
                    <p><strong>Next Run:</strong> ${nextRun}</p>
                    <p><strong>Last Run:</strong> ${lastRun}</p>
                    
                    ${schedule.target_roles && schedule.target_roles.length > 0 ? 
                        `<p><strong>Target Roles:</strong> ${schedule.target_roles.join(', ')}</p>` : ''}
                    
                    ${schedule.delivery_channels && schedule.delivery_channels.length > 0 ? 
                        `<p><strong>Channels:</strong> ${schedule.delivery_channels.join(', ')}</p>` : ''}
                </div>
                
                <div class="schedule-actions">
                    <button onclick="reportScheduler.executeSchedule('${schedule.schedule_id}')" 
                            class="btn btn-small btn-primary">Execute Now</button>
                    <button onclick="reportScheduler.editSchedule('${schedule.schedule_id}')" 
                            class="btn btn-small btn-secondary">Edit</button>
                    <button onclick="reportScheduler.toggleSchedule('${schedule.schedule_id}', ${!schedule.is_active})" 
                            class="btn btn-small ${schedule.is_active ? 'btn-warning' : 'btn-success'}">
                        ${schedule.is_active ? 'Disable' : 'Enable'}
                    </button>
                    <button onclick="reportScheduler.deleteSchedule('${schedule.schedule_id}')" 
                            class="btn btn-small btn-danger">Delete</button>
                </div>
            </div>
        `;
    }
    
    formatScheduleType(type) {
        const types = {
            'cron': 'Cron Schedule',
            'interval': 'Interval',
            'event_driven': 'Event-Driven'
        };
        return types[type] || type;
    }
    
    async handleCreateSchedule(event) {
        event.preventDefault();
        
        const formData = new FormData(event.target);
        const scheduleData = this.serializeFormData(formData);
        
        try {
            const response = await fetch(`${this.apiBase}/schedules`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${localStorage.getItem('token')}`
                },
                body: JSON.stringify(scheduleData)
            });
            
            if (!response.ok) {
                throw new Error(`Failed to create schedule: ${response.statusText}`);
            }
            
            const result = await response.json();
            this.showSuccess(`Schedule "${result.name}" created successfully!`);
            
            // Reset form and reload schedules
            event.target.reset();
            this.loadSchedules();
            showTab('schedules');
            
        } catch (error) {
            console.error('Failed to create schedule:', error);
            this.showError(`Failed to create schedule: ${error.message}`);
        }
    }
    
    serializeFormData(formData) {
        const data = {};
        
        for (let [key, value] of formData.entries()) {
            if (key === 'target_roles' || key === 'delivery_channels') {
                if (!data[key]) data[key] = [];
                data[key].push(value);
            } else if (key === 'force_delivery' || key === 'include_attachments') {
                data[key] = value === 'on';
            } else if (key === 'max_retries' || key === 'retry_delay_minutes' || key === 'interval_minutes' || key === 'trigger_threshold') {
                data[key] = parseInt(value) || 0;
            } else {
                data[key] = value;
            }
        }
        
        return data;
    }
    
    async executeSchedule(scheduleId) {
        try {
            const response = await fetch(`${this.apiBase}/schedules/${scheduleId}/execute`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${localStorage.getItem('token')}`
                }
            });
            
            if (!response.ok) {
                throw new Error(`Failed to execute schedule: ${response.statusText}`);
            }
            
            const result = await response.json();
            this.showSuccess(`Schedule executed successfully! Status: ${result.status}`);
            
            // Reload schedules to update last run time
            this.loadSchedules();
            
        } catch (error) {
            console.error('Failed to execute schedule:', error);
            this.showError(`Failed to execute schedule: ${error.message}`);
        }
    }
    
    async toggleSchedule(scheduleId, isActive) {
        try {
            const response = await fetch(`${this.apiBase}/schedules/${scheduleId}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${localStorage.getItem('token')}`
                },
                body: JSON.stringify({ is_active: isActive })
            });
            
            if (!response.ok) {
                throw new Error(`Failed to update schedule: ${response.statusText}`);
            }
            
            this.showSuccess(`Schedule ${isActive ? 'enabled' : 'disabled'} successfully!`);
            this.loadSchedules();
            
        } catch (error) {
            console.error('Failed to toggle schedule:', error);
            this.showError(`Failed to toggle schedule: ${error.message}`);
        }
    }
    
    async deleteSchedule(scheduleId) {
        if (!confirm('Are you sure you want to delete this schedule? This action cannot be undone.')) {
            return;
        }
        
        try {
            const response = await fetch(`${this.apiBase}/schedules/${scheduleId}`, {
                method: 'DELETE',
                headers: {
                    'Authorization': `Bearer ${localStorage.getItem('token')}`
                }
            });
            
            if (!response.ok) {
                throw new Error(`Failed to delete schedule: ${response.statusText}`);
            }
            
            this.showSuccess('Schedule deleted successfully!');
            this.loadSchedules();
            
        } catch (error) {
            console.error('Failed to delete schedule:', error);
            this.showError(`Failed to delete schedule: ${error.message}`);
        }
    }
    
    editSchedule(scheduleId) {
        // For now, just show a message - full edit functionality could be implemented later
        this.showInfo('Edit functionality will be implemented in a future update.');
    }
    
    loadScheduleOptions() {
        // Populate schedule dropdown for history view
        const historySelect = document.getElementById('history-schedule');
        if (historySelect) {
            this.schedules.forEach(schedule => {
                const option = document.createElement('option');
                option.value = schedule.schedule_id;
                option.textContent = schedule.name;
                historySelect.appendChild(option);
            });
        }
    }
    
    async loadExecutionHistory() {
        const scheduleId = document.getElementById('history-schedule').value;
        const limit = document.getElementById('history-limit').value;
        
        try {
            let url = `${this.apiBase}/schedules/run-due`;
            if (scheduleId) {
                url = `${this.apiBase}/schedules/${scheduleId}/history?limit=${limit}`;
            }
            
            const response = await fetch(url, {
                headers: {
                    'Authorization': `Bearer ${localStorage.getItem('token')}`
                }
            });
            
            if (!response.ok) {
                throw new Error(`Failed to load execution history: ${response.statusText}`);
            }
            
            const history = await response.json();
            this.renderExecutionHistory(history);
            
        } catch (error) {
            console.error('Failed to load execution history:', error);
            this.showError(`Failed to load execution history: ${error.message}`);
        }
    }
    
    renderExecutionHistory(history) {
        const container = document.getElementById('execution-history');
        if (!container) return;
        
        if (!Array.isArray(history) || history.length === 0) {
            container.innerHTML = '<p>No execution history found.</p>';
            return;
        }
        
        container.innerHTML = history.map(execution => this.renderExecutionItem(execution)).join('');
    }
    
    renderExecutionItem(execution) {
        const statusClass = `execution-${execution.status}`;
        const executionTime = new Date(execution.execution_time).toLocaleString();
        
        return `
            <div class="execution-item ${statusClass}">
                <strong>${execution.schedule_id}</strong> - ${executionTime}
                <br>
                Status: ${execution.status.toUpperCase()}
                ${execution.report_generated ? ' | Report Generated: Yes' : ' | Report Generated: No'}
                ${execution.users_notified > 0 ? ` | Users Notified: ${execution.users_notified}` : ''}
                ${execution.users_failed > 0 ? ` | Users Failed: ${execution.users_failed}` : ''}
                ${execution.execution_duration_seconds ? ` | Duration: ${execution.execution_duration_seconds.toFixed(2)}s` : ''}
                ${execution.error_message ? `<br><em>Error: ${execution.error_message}</em>` : ''}
            </div>
        `;
    }
    
    showSuccess(message) {
        // Simple success message - could be enhanced with a proper notification system
        alert(`Success: ${message}`);
    }
    
    showError(message) {
        // Simple error message - could be enhanced with a proper notification system
        alert(`Error: ${message}`);
    }
    
    showInfo(message) {
        // Simple info message - could be enhanced with a proper notification system
        alert(`Info: ${message}`);
    }
}

// Global functions for tab switching
function showTab(tabName) {
    // Hide all tab contents
    const tabContents = document.querySelectorAll('.tab-content');
    tabContents.forEach(content => content.classList.remove('active'));
    
    // Remove active class from all tabs
    const tabs = document.querySelectorAll('.tab');
    tabs.forEach(tab => tab.classList.remove('active'));
    
    // Show selected tab content
    const selectedContent = document.getElementById(tabName);
    if (selectedContent) {
        selectedContent.classList.add('active');
    }
    
    // Add active class to selected tab
    const selectedTab = document.querySelector(`[onclick="showTab('${tabName}')"]`);
    if (selectedTab) {
        selectedTab.classList.add('active');
    }
    
    // Update current tab
    if (window.reportScheduler) {
        window.reportScheduler.currentTab = tabName;
    }
    
    // Load data for specific tabs
    if (tabName === 'history') {
        window.reportScheduler.loadExecutionHistory();
    }
}

function toggleScheduleOptions() {
    const scheduleType = document.getElementById('schedule-type').value;
    
    // Hide all option sections
    const optionSections = document.querySelectorAll('.schedule-options');
    optionSections.forEach(section => section.style.display = 'none');
    
    // Show relevant options based on schedule type
    switch (scheduleType) {
        case 'cron':
            document.getElementById('cron-options').style.display = 'block';
            break;
        case 'interval':
            document.getElementById('interval-options').style.display = 'block';
            break;
        case 'event_driven':
            document.getElementById('event-options').style.display = 'block';
            break;
    }
}

// Initialize the report scheduler when the page loads
document.addEventListener('DOMContentLoaded', function() {
    window.reportScheduler = new ReportScheduler();
}); 