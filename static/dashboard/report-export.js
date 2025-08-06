/**
 * Report Export JavaScript
 * 
 * Handles the report export interface functionality including:
 * - Tab switching
 * - Format selection
 * - Form validation
 * - API calls for export generation
 * - Download handling
 * - Export history management
 */

class ReportExportManager {
    constructor() {
        this.currentTab = 'weekly';
        this.selectedFormat = 'pdf';
        this.initializeEventListeners();
        this.setDefaultDates();
        this.loadExportHistory();
    }
    
    initializeEventListeners() {
        // Tab switching
        document.querySelectorAll('.export-tab').forEach(tab => {
            tab.addEventListener('click', () => {
                this.switchTab(tab.dataset.tab);
            });
        });
        
        // Format selection
        document.querySelectorAll('.format-selector').forEach(selector => {
            selector.addEventListener('click', (e) => {
                if (e.target.closest('.format-option')) {
                    const option = e.target.closest('.format-option');
                    this.selectFormat(option, selector);
                }
            });
        });
    }
    
    switchTab(tabName) {
        // Update active tab
        document.querySelectorAll('.export-tab').forEach(tab => {
            tab.classList.remove('active');
        });
        document.querySelector(`[data-tab="${tabName}"]`).classList.add('active');
        
        // Update active content
        document.querySelectorAll('.export-content').forEach(content => {
            content.classList.remove('active');
        });
        document.getElementById(`${tabName}-tab`).classList.add('active');
        
        this.currentTab = tabName;
        
        // Load specific data for the tab
        if (tabName === 'history') {
            this.loadExportHistory();
        }
    }
    
    selectFormat(selectedOption, selector) {
        // Remove selected class from all options in this selector
        selector.querySelectorAll('.format-option').forEach(option => {
            option.classList.remove('selected');
        });
        
        // Add selected class to clicked option
        selectedOption.classList.add('selected');
        
        // Update selected format
        this.selectedFormat = selectedOption.dataset.format;
    }
    
    setDefaultDates() {
        const now = new Date();
        const oneWeekAgo = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);
        
        // Set default dates for weekly reports
        document.getElementById('weekly-start-date').value = this.formatDateTimeLocal(oneWeekAgo);
        document.getElementById('weekly-end-date').value = this.formatDateTimeLocal(now);
        
        // Set default dates for analytics reports
        document.getElementById('analytics-start-date').value = this.formatDateTimeLocal(oneWeekAgo);
        document.getElementById('analytics-end-date').value = this.formatDateTimeLocal(now);
    }
    
    formatDateTimeLocal(date) {
        const year = date.getFullYear();
        const month = String(date.getMonth() + 1).padStart(2, '0');
        const day = String(date.getDate()).padStart(2, '0');
        const hours = String(date.getHours()).padStart(2, '0');
        const minutes = String(date.getMinutes()).padStart(2, '0');
        
        return `${year}-${month}-${day}T${hours}:${minutes}`;
    }
    
    getSelectedFormat(selectorId) {
        const selector = document.querySelector(selectorId);
        const selectedOption = selector.querySelector('.format-option.selected');
        return selectedOption ? selectedOption.dataset.format : 'pdf';
    }
    
    async exportWeeklyReport() {
        try {
            this.showLoading();
            
            const request = {
                start_date: document.getElementById('weekly-start-date').value,
                end_date: document.getElementById('weekly-end-date').value,
                format: this.getSelectedFormat('#weekly-tab .format-selector'),
                include_charts: document.getElementById('weekly-include-charts').checked,
                include_analytics: document.getElementById('weekly-include-analytics').checked,
                custom_title: document.getElementById('weekly-custom-title').value || null
            };
            
            const response = await this.callExportAPI('/api/reports/export/weekly', request);
            
            if (response.success) {
                this.showAlert('success', 'Weekly report export generated successfully!');
                await this.downloadExport(response.data.download_url, response.data.filename);
                this.loadExportHistory(); // Refresh history
            } else {
                this.showAlert('error', `Export failed: ${response.error}`);
            }
        } catch (error) {
            console.error('Weekly report export error:', error);
            this.showAlert('error', 'Failed to export weekly report. Please try again.');
        } finally {
            this.hideLoading();
        }
    }
    
    async exportAnalyticsReport() {
        try {
            this.showLoading();
            
            const request = {
                start_date: document.getElementById('analytics-start-date').value,
                end_date: document.getElementById('analytics-end-date').value,
                format: this.getSelectedFormat('#analytics-tab .format-selector'),
                include_predictions: document.getElementById('analytics-include-predictions').checked,
                include_anomalies: document.getElementById('analytics-include-anomalies').checked,
                include_correlations: document.getElementById('analytics-include-correlations').checked
            };
            
            const response = await this.callExportAPI('/api/reports/export/analytics', request);
            
            if (response.success) {
                this.showAlert('success', 'Analytics report export generated successfully!');
                await this.downloadExport(response.data.download_url, response.data.filename);
                this.loadExportHistory(); // Refresh history
            } else {
                this.showAlert('error', `Export failed: ${response.error}`);
            }
        } catch (error) {
            console.error('Analytics report export error:', error);
            this.showAlert('error', 'Failed to export analytics report. Please try again.');
        } finally {
            this.hideLoading();
        }
    }
    
    async exportArchiveReport() {
        try {
            this.showLoading();
            
            const reportId = document.getElementById('archive-report-id').value.trim();
            if (!reportId) {
                this.showAlert('error', 'Please enter a report ID');
                return;
            }
            
            const request = {
                report_id: reportId,
                format: this.getSelectedFormat('#archive-tab .format-selector'),
                include_metadata: document.getElementById('archive-include-metadata').checked
            };
            
            const response = await this.callExportAPI('/api/reports/export/archive', request);
            
            if (response.success) {
                this.showAlert('success', 'Archive report export generated successfully!');
                await this.downloadExport(response.data.download_url, response.data.filename);
                this.loadExportHistory(); // Refresh history
            } else {
                this.showAlert('error', `Export failed: ${response.error}`);
            }
        } catch (error) {
            console.error('Archive report export error:', error);
            this.showAlert('error', 'Failed to export archive report. Please try again.');
        } finally {
            this.hideLoading();
        }
    }
    
    async exportCustomReport() {
        try {
            this.showLoading();
            
            const reportType = document.getElementById('custom-report-type').value.trim();
            const reportDataText = document.getElementById('custom-report-data').value.trim();
            
            if (!reportType) {
                this.showAlert('error', 'Please enter a report type');
                return;
            }
            
            if (!reportDataText) {
                this.showAlert('error', 'Please enter report data');
                return;
            }
            
            let reportData;
            try {
                reportData = JSON.parse(reportDataText);
            } catch (e) {
                this.showAlert('error', 'Invalid JSON format for report data');
                return;
            }
            
            const request = {
                report_data: reportData,
                format: this.getSelectedFormat('#custom-tab .format-selector'),
                report_type: reportType,
                include_charts: document.getElementById('custom-include-charts').checked
            };
            
            const response = await this.callExportAPI('/api/reports/export/custom', request);
            
            if (response.success) {
                this.showAlert('success', 'Custom report export generated successfully!');
                await this.downloadExport(response.data.download_url, response.data.filename);
                this.loadExportHistory(); // Refresh history
            } else {
                this.showAlert('error', `Export failed: ${response.error}`);
            }
        } catch (error) {
            console.error('Custom report export error:', error);
            this.showAlert('error', 'Failed to export custom report. Please try again.');
        } finally {
            this.hideLoading();
        }
    }
    
    async callExportAPI(endpoint, requestData) {
        const token = this.getAuthToken();
        if (!token) {
            throw new Error('Authentication required');
        }
        
        const response = await fetch(endpoint, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify(requestData)
        });
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Export request failed');
        }
        
        const data = await response.json();
        return { success: true, data };
    }
    
    async downloadExport(downloadUrl, filename) {
        try {
            const token = this.getAuthToken();
            const response = await fetch(downloadUrl, {
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            });
            
            if (!response.ok) {
                throw new Error('Download failed');
            }
            
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = filename;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
            
        } catch (error) {
            console.error('Download error:', error);
            this.showAlert('error', 'Failed to download export file');
        }
    }
    
    async loadExportHistory() {
        try {
            const token = this.getAuthToken();
            const response = await fetch('/api/reports/export/history', {
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            });
            
            if (!response.ok) {
                throw new Error('Failed to load export history');
            }
            
            const data = await response.json();
            this.displayExportHistory(data.exports);
            
        } catch (error) {
            console.error('Export history error:', error);
            this.showAlert('error', 'Failed to load export history');
        }
    }
    
    displayExportHistory(exports) {
        const tbody = document.getElementById('history-table-body');
        tbody.innerHTML = '';
        
        if (!exports || exports.length === 0) {
            tbody.innerHTML = '<tr><td colspan="8" style="text-align: center; color: #666;">No export history found</td></tr>';
            return;
        }
        
        exports.forEach(exportItem => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>${this.escapeHtml(exportItem.export_id)}</td>
                <td>${this.escapeHtml(exportItem.type)}</td>
                <td>${this.escapeHtml(exportItem.format.toUpperCase())}</td>
                <td>${this.escapeHtml(exportItem.filename)}</td>
                <td>${this.formatFileSize(exportItem.size_bytes)}</td>
                <td>${this.formatDate(exportItem.created_at)}</td>
                <td><span class="status-badge status-${exportItem.status}">${exportItem.status}</span></td>
                <td>
                    <button class="btn btn-success" onclick="downloadExport('${exportItem.export_id}')" style="padding: 4px 8px; font-size: 12px;">Download</button>
                    <button class="btn btn-secondary" onclick="deleteExport('${exportItem.export_id}')" style="padding: 4px 8px; font-size: 12px;">Delete</button>
                </td>
            `;
            tbody.appendChild(row);
        });
    }
    
    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }
    
    formatDate(dateString) {
        const date = new Date(dateString);
        return date.toLocaleDateString() + ' ' + date.toLocaleTimeString();
    }
    
    async deleteExport(exportId) {
        if (!confirm('Are you sure you want to delete this export?')) {
            return;
        }
        
        try {
            const token = this.getAuthToken();
            const response = await fetch(`/api/reports/export/${exportId}`, {
                method: 'DELETE',
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            });
            
            if (!response.ok) {
                throw new Error('Failed to delete export');
            }
            
            this.showAlert('success', 'Export deleted successfully');
            this.loadExportHistory(); // Refresh history
            
        } catch (error) {
            console.error('Delete export error:', error);
            this.showAlert('error', 'Failed to delete export');
        }
    }
    
    showLoading() {
        document.getElementById('loading').style.display = 'block';
    }
    
    hideLoading() {
        document.getElementById('loading').style.display = 'none';
    }
    
    showAlert(type, message) {
        const alert = document.getElementById('alert');
        alert.className = `alert alert-${type}`;
        alert.textContent = message;
        alert.style.display = 'block';
        
        // Auto-hide after 5 seconds
        setTimeout(() => {
            alert.style.display = 'none';
        }, 5000);
    }
    
    getAuthToken() {
        return localStorage.getItem('auth_token');
    }
    
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// Global functions for onclick handlers
let exportManager;

document.addEventListener('DOMContentLoaded', () => {
    exportManager = new ReportExportManager();
});

function exportWeeklyReport() {
    exportManager.exportWeeklyReport();
}

function exportAnalyticsReport() {
    exportManager.exportAnalyticsReport();
}

function exportArchiveReport() {
    exportManager.exportArchiveReport();
}

function exportCustomReport() {
    exportManager.exportCustomReport();
}

function loadExportHistory() {
    exportManager.loadExportHistory();
}

function downloadExport(exportId) {
    // This would be implemented to download a specific export
    console.log('Download export:', exportId);
}

function deleteExport(exportId) {
    exportManager.deleteExport(exportId);
} 