/**
 * Report Archiving & Historical Access JavaScript
 * 
 * This module provides comprehensive functionality for managing archived reports,
 * including search, retrieval, archiving, and management operations.
 */

class ReportArchivingManager {
    constructor() {
        this.currentPage = 1;
        this.pageSize = 12;
        this.currentSearchParams = {};
        this.tags = [];
        
        this.initializeEventListeners();
        this.loadRecentReports();
        this.loadStatistics();
    }
    
    initializeEventListeners() {
        // Tab switching
        document.querySelectorAll('.archive-tab').forEach(tab => {
            tab.addEventListener('click', () => this.switchTab(tab.dataset.tab));
        });
        
        // Search form
        document.getElementById('search-form').addEventListener('submit', (e) => {
            e.preventDefault();
            this.performSearch();
        });
        
        // Clear search
        document.getElementById('clear-search').addEventListener('click', () => {
            this.clearSearchForm();
            this.loadRecentReports();
        });
        
        // Archive form
        document.getElementById('archive-form').addEventListener('submit', (e) => {
            e.preventDefault();
            this.archiveReport();
        });
        
        // Clear archive form
        document.getElementById('clear-archive').addEventListener('click', () => {
            this.clearArchiveForm();
        });
        
        // Management buttons
        document.getElementById('run-cleanup').addEventListener('click', () => this.runCleanup());
        document.getElementById('export-metadata').addEventListener('click', () => this.exportMetadata());
        document.getElementById('refresh-stats').addEventListener('click', () => this.loadStatistics());
        
        // Pagination
        document.getElementById('prev-page').addEventListener('click', () => this.previousPage());
        document.getElementById('next-page').addEventListener('click', () => this.nextPage());
        
        // Modal
        document.getElementById('close-modal').addEventListener('click', () => this.closeModal());
        document.getElementById('report-modal').addEventListener('click', (e) => {
            if (e.target.id === 'report-modal') this.closeModal();
        });
        
        // Tags input
        this.initializeTagsInput();
    }
    
    switchTab(tabName) {
        // Update active tab
        document.querySelectorAll('.archive-tab').forEach(tab => {
            tab.classList.remove('active');
        });
        document.querySelector(`[data-tab="${tabName}"]`).classList.add('active');
        
        // Update active content
        document.querySelectorAll('.archive-content').forEach(content => {
            content.classList.remove('active');
        });
        document.getElementById(`${tabName}-tab`).classList.add('active');
        
        // Load appropriate data
        switch(tabName) {
            case 'search':
                this.loadRecentReports();
                break;
            case 'statistics':
                this.loadStatistics();
                break;
            case 'management':
                this.loadManagementData();
                break;
        }
    }
    
    async performSearch() {
        const searchParams = {
            title_search: document.getElementById('search-title').value,
            report_type: document.getElementById('search-type').value,
            date_from: document.getElementById('search-date-from').value,
            date_to: document.getElementById('search-date-to').value,
            tags: document.getElementById('search-tags').value,
            access_level: document.getElementById('search-access').value,
            limit: this.pageSize,
            offset: (this.currentPage - 1) * this.pageSize
        };
        
        this.currentSearchParams = searchParams;
        await this.searchReports(searchParams);
    }
    
    async searchReports(params) {
        try {
            this.showLoading('search-results');
            
            const queryString = new URLSearchParams();
            Object.entries(params).forEach(([key, value]) => {
                if (value) queryString.append(key, value);
            });
            
            const response = await fetch(`/api/reports/archiving/search?${queryString}`, {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${this.getAuthToken()}`
                }
            });
            
            if (!response.ok) {
                throw new Error(`Search failed: ${response.statusText}`);
            }
            
            const data = await response.json();
            this.displaySearchResults(data);
            
        } catch (error) {
            console.error('Search error:', error);
            this.showError('search-results', 'Failed to search reports: ' + error.message);
        }
    }
    
    displaySearchResults(data) {
        const container = document.getElementById('search-results');
        
        if (data.reports.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <h3>No Reports Found</h3>
                    <p>No archived reports match your search criteria.</p>
                </div>
            `;
            document.getElementById('search-pagination').style.display = 'none';
            return;
        }
        
        const reportsHtml = data.reports.map(report => this.createReportCard(report)).join('');
        
        container.innerHTML = `
            <div class="reports-grid">
                ${reportsHtml}
            </div>
        `;
        
        // Update pagination
        this.updatePagination(data);
        
        // Add event listeners to report cards
        this.addReportCardListeners();
    }
    
    createReportCard(report) {
        const formatDate = (dateString) => {
            return new Date(dateString).toLocaleDateString('en-US', {
                year: 'numeric',
                month: 'short',
                day: 'numeric',
                hour: '2-digit',
                minute: '2-digit'
            });
        };
        
        const formatFileSize = (bytes) => {
            if (bytes < 1024) return bytes + ' B';
            if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
            return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
        };
        
        return `
            <div class="report-card" data-report-id="${report.report_id}">
                <div class="report-header">
                    <h4 class="report-title">${this.escapeHtml(report.title)}</h4>
                    <div class="report-meta">
                        <span class="report-type">${report.report_type.replace('_', ' ').toUpperCase()}</span>
                        <span>${formatDate(report.generated_at)}</span>
                    </div>
                </div>
                <div class="report-body">
                    ${report.description ? `<p class="report-description">${this.escapeHtml(report.description)}</p>` : ''}
                    <div class="report-details">
                        <div class="detail-item">
                            <span class="detail-label">Period</span>
                            <span class="detail-value">${formatDate(report.report_period_start)} - ${formatDate(report.report_period_end)}</span>
                        </div>
                        <div class="detail-item">
                            <span class="detail-label">Size</span>
                            <span class="detail-value">${formatFileSize(report.file_size_bytes)}</span>
                        </div>
                        <div class="detail-item">
                            <span class="detail-label">Access</span>
                            <span class="detail-value">${report.access_level.toUpperCase()}</span>
                        </div>
                        <div class="detail-item">
                            <span class="detail-label">Status</span>
                            <span class="detail-value">${report.status.toUpperCase()}</span>
                        </div>
                    </div>
                    ${report.tags.length > 0 ? `
                        <div class="report-tags" style="margin-bottom: 15px;">
                            ${report.tags.map(tag => `<span class="tag" style="margin-right: 5px;">${this.escapeHtml(tag)}</span>`).join('')}
                        </div>
                    ` : ''}
                    <div class="report-actions">
                        <button class="btn btn-primary btn-sm view-report">👁️ View</button>
                        <button class="btn btn-secondary btn-sm download-report">📥 Download</button>
                        <button class="btn btn-danger btn-sm delete-report">🗑️ Delete</button>
                    </div>
                </div>
            </div>
        `;
    }
    
    addReportCardListeners() {
        document.querySelectorAll('.view-report').forEach(button => {
            button.addEventListener('click', (e) => {
                const reportId = e.target.closest('.report-card').dataset.reportId;
                this.viewReport(reportId);
            });
        });
        
        document.querySelectorAll('.download-report').forEach(button => {
            button.addEventListener('click', (e) => {
                const reportId = e.target.closest('.report-card').dataset.reportId;
                this.downloadReport(reportId);
            });
        });
        
        document.querySelectorAll('.delete-report').forEach(button => {
            button.addEventListener('click', (e) => {
                const reportId = e.target.closest('.report-card').dataset.reportId;
                this.deleteReport(reportId);
            });
        });
    }
    
    async viewReport(reportId) {
        try {
            const response = await fetch(`/api/reports/archiving/reports/${reportId}`, {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${this.getAuthToken()}`
                }
            });
            
            if (!response.ok) {
                throw new Error(`Failed to retrieve report: ${response.statusText}`);
            }
            
            const reportData = await response.json();
            this.showReportModal(reportData, reportId);
            
        } catch (error) {
            console.error('View report error:', error);
            this.showAlert('error', 'Failed to view report: ' + error.message);
        }
    }
    
    showReportModal(reportData, reportId) {
        const modal = document.getElementById('report-modal');
        const modalTitle = document.getElementById('modal-title');
        const modalContent = document.getElementById('modal-content');
        
        modalTitle.textContent = `Report: ${reportId}`;
        
        modalContent.innerHTML = `
            <div style="max-height: 60vh; overflow-y: auto;">
                <pre style="background: #f8f9fa; padding: 15px; border-radius: 5px; font-size: 12px; white-space: pre-wrap;">${JSON.stringify(reportData, null, 2)}</pre>
            </div>
        `;
        
        modal.style.display = 'block';
    }
    
    closeModal() {
        document.getElementById('report-modal').style.display = 'none';
    }
    
    async downloadReport(reportId) {
        try {
            const response = await fetch(`/api/reports/archiving/reports/${reportId}`, {
                method: 'GET',
                headers: {
                    'Authorization': `Bearer ${this.getAuthToken()}`
                }
            });
            
            if (!response.ok) {
                throw new Error(`Failed to download report: ${response.statusText}`);
            }
            
            const reportData = await response.json();
            const blob = new Blob([JSON.stringify(reportData, null, 2)], { type: 'application/json' });
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `${reportId}.json`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            window.URL.revokeObjectURL(url);
            
            this.showAlert('success', 'Report downloaded successfully');
            
        } catch (error) {
            console.error('Download error:', error);
            this.showAlert('error', 'Failed to download report: ' + error.message);
        }
    }
    
    async deleteReport(reportId) {
        if (!confirm('Are you sure you want to delete this report? This action cannot be undone.')) {
            return;
        }
        
        try {
            const response = await fetch(`/api/reports/archiving/reports/${reportId}`, {
                method: 'DELETE',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${this.getAuthToken()}`
                }
            });
            
            if (!response.ok) {
                throw new Error(`Failed to delete report: ${response.statusText}`);
            }
            
            this.showAlert('success', 'Report deleted successfully');
            this.performSearch(); // Refresh the search results
            
        } catch (error) {
            console.error('Delete error:', error);
            this.showAlert('error', 'Failed to delete report: ' + error.message);
        }
    }
    
    async archiveReport() {
        const formData = {
            title: document.getElementById('archive-title').value,
            report_type: document.getElementById('archive-type').value,
            description: document.getElementById('archive-description').value,
            retention_days: parseInt(document.getElementById('archive-retention').value),
            access_level: document.getElementById('archive-access').value,
            tags: this.tags,
            report_data: JSON.parse(document.getElementById('archive-data').value)
        };
        
        try {
            const response = await fetch('/api/reports/archiving/archive', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${this.getAuthToken()}`
                },
                body: JSON.stringify(formData)
            });
            
            if (!response.ok) {
                throw new Error(`Failed to archive report: ${response.statusText}`);
            }
            
            const result = await response.json();
            this.showAlert('success', `Report archived successfully: ${result.report_id}`);
            this.clearArchiveForm();
            
        } catch (error) {
            console.error('Archive error:', error);
            this.showAlert('error', 'Failed to archive report: ' + error.message);
        }
    }
    
    async loadRecentReports() {
        try {
            const response = await fetch(`/api/reports/archiving/recent?limit=${this.pageSize}`, {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${this.getAuthToken()}`
                }
            });
            
            if (!response.ok) {
                throw new Error(`Failed to load recent reports: ${response.statusText}`);
            }
            
            const reports = await response.json();
            this.displaySearchResults({ reports, total_count: reports.length, has_more: false });
            
        } catch (error) {
            console.error('Load recent reports error:', error);
            this.showError('search-results', 'Failed to load recent reports: ' + error.message);
        }
    }
    
    async loadStatistics() {
        try {
            const response = await fetch('/api/reports/archiving/statistics', {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${this.getAuthToken()}`
                }
            });
            
            if (!response.ok) {
                throw new Error(`Failed to load statistics: ${response.statusText}`);
            }
            
            const stats = await response.json();
            this.displayStatistics(stats);
            
        } catch (error) {
            console.error('Load statistics error:', error);
            this.showError('statistics-grid', 'Failed to load statistics: ' + error.message);
        }
    }
    
    displayStatistics(stats) {
        const container = document.getElementById('statistics-grid');
        
        const formatDate = (dateString) => {
            if (!dateString) return 'N/A';
            return new Date(dateString).toLocaleDateString('en-US', {
                year: 'numeric',
                month: 'short',
                day: 'numeric'
            });
        };
        
        container.innerHTML = `
            <div class="stat-card">
                <div class="stat-number">${stats.total_reports}</div>
                <div class="stat-label">Total Reports</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">${stats.total_storage_mb}</div>
                <div class="stat-label">Storage Used (MB)</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">${Object.keys(stats.reports_by_type).length}</div>
                <div class="stat-label">Report Types</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">${formatDate(stats.oldest_report)}</div>
                <div class="stat-label">Oldest Report</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">${formatDate(stats.newest_report)}</div>
                <div class="stat-label">Newest Report</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">${stats.reports_by_status.active || 0}</div>
                <div class="stat-label">Active Reports</div>
            </div>
        `;
    }
    
    async runCleanup() {
        if (!confirm('Are you sure you want to run cleanup? This will remove expired reports.')) {
            return;
        }
        
        try {
            const response = await fetch('/api/reports/archiving/cleanup', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${this.getAuthToken()}`
                }
            });
            
            if (!response.ok) {
                throw new Error(`Failed to run cleanup: ${response.statusText}`);
            }
            
            const result = await response.json();
            this.showAlert('success', `Cleanup initiated. Found ${result.expired_reports_found} expired reports.`);
            
            // Refresh statistics after cleanup
            setTimeout(() => this.loadStatistics(), 2000);
            
        } catch (error) {
            console.error('Cleanup error:', error);
            this.showAlert('error', 'Failed to run cleanup: ' + error.message);
        }
    }
    
    async exportMetadata() {
        try {
            const response = await fetch('/api/reports/archiving/export/metadata?format=json', {
                method: 'GET',
                headers: {
                    'Authorization': `Bearer ${this.getAuthToken()}`
                }
            });
            
            if (!response.ok) {
                throw new Error(`Failed to export metadata: ${response.statusText}`);
            }
            
            const result = await response.json();
            const blob = new Blob([result.content], { type: 'application/json' });
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = result.filename;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            window.URL.revokeObjectURL(url);
            
            this.showAlert('success', 'Metadata exported successfully');
            
        } catch (error) {
            console.error('Export error:', error);
            this.showAlert('error', 'Failed to export metadata: ' + error.message);
        }
    }
    
    loadManagementData() {
        // This could load additional management data if needed
        document.getElementById('management-results').innerHTML = `
            <div class="empty-state">
                <h3>Archive Management</h3>
                <p>Use the buttons above to manage your archive</p>
            </div>
        `;
    }
    
    initializeTagsInput() {
        const tagsContainer = document.getElementById('archive-tags');
        const tagInput = tagsContainer.querySelector('.tag-input');
        
        tagInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                const tag = tagInput.value.trim();
                if (tag && !this.tags.includes(tag)) {
                    this.tags.push(tag);
                    this.renderTags();
                }
                tagInput.value = '';
            }
        });
    }
    
    renderTags() {
        const tagsContainer = document.getElementById('archive-tags');
        const tagInput = tagsContainer.querySelector('.tag-input');
        
        // Clear existing tags
        tagsContainer.innerHTML = '';
        
        // Add tag elements
        this.tags.forEach(tag => {
            const tagElement = document.createElement('span');
            tagElement.className = 'tag';
            tagElement.innerHTML = `
                ${this.escapeHtml(tag)}
                <span class="tag-remove" onclick="archivingManager.removeTag('${tag}')">&times;</span>
            `;
            tagsContainer.appendChild(tagElement);
        });
        
        // Add input back
        tagsContainer.appendChild(tagInput);
    }
    
    removeTag(tag) {
        this.tags = this.tags.filter(t => t !== tag);
        this.renderTags();
    }
    
    clearSearchForm() {
        document.getElementById('search-form').reset();
        this.currentPage = 1;
        this.currentSearchParams = {};
    }
    
    clearArchiveForm() {
        document.getElementById('archive-form').reset();
        this.tags = [];
        this.renderTags();
    }
    
    updatePagination(data) {
        const pagination = document.getElementById('search-pagination');
        const pageInfo = document.getElementById('page-info');
        const prevButton = document.getElementById('prev-page');
        const nextButton = document.getElementById('next-page');
        
        const totalPages = Math.ceil(data.total_count / this.pageSize);
        
        pageInfo.textContent = `Page ${this.currentPage} of ${totalPages}`;
        prevButton.disabled = this.currentPage <= 1;
        nextButton.disabled = this.currentPage >= totalPages;
        
        pagination.style.display = totalPages > 1 ? 'flex' : 'none';
    }
    
    previousPage() {
        if (this.currentPage > 1) {
            this.currentPage--;
            this.performSearch();
        }
    }
    
    nextPage() {
        this.currentPage++;
        this.performSearch();
    }
    
    showLoading(containerId) {
        document.getElementById(containerId).innerHTML = '<div class="loading">Loading...</div>';
    }
    
    showError(containerId, message) {
        document.getElementById(containerId).innerHTML = `
            <div class="alert alert-error">
                <strong>Error:</strong> ${this.escapeHtml(message)}
            </div>
        `;
    }
    
    showAlert(type, message) {
        const alertClass = type === 'success' ? 'alert-success' : 
                          type === 'error' ? 'alert-error' : 'alert-warning';
        
        const alert = document.createElement('div');
        alert.className = `alert ${alertClass}`;
        alert.innerHTML = this.escapeHtml(message);
        
        // Insert at the top of the container
        const container = document.querySelector('.archive-container');
        container.insertBefore(alert, container.firstChild);
        
        // Remove after 5 seconds
        setTimeout(() => {
            if (alert.parentNode) {
                alert.parentNode.removeChild(alert);
            }
        }, 5000);
    }
    
    getAuthToken() {
        // Get token from localStorage or wherever it's stored
        return localStorage.getItem('authToken') || '';
    }
    
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// Initialize the archiving manager when the page loads
let archivingManager;
document.addEventListener('DOMContentLoaded', () => {
    archivingManager = new ReportArchivingManager();
}); 