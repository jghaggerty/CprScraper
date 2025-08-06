/**
 * Bulk Export Manager JavaScript
 * 
 * Handles the frontend interface for bulk export operations
 * including data source selection, configuration, and progress tracking.
 */

class BulkExportManager {
    constructor() {
        this.currentStep = 1;
        this.selectedSources = [];
        this.currentJobId = null;
        this.progressInterval = null;
        this.dataSources = [];
        this.activeJobs = [];
        
        this.init();
    }

    async init() {
        try {
            await this.loadDataSources();
            await this.loadActiveJobs();
            this.renderDataSources();
            this.renderActiveJobs();
        } catch (error) {
            console.error('Failed to initialize bulk export manager:', error);
            this.showAlert('Failed to load export interface. Please refresh the page.', 'error');
        }
    }

    async loadDataSources() {
        try {
            const response = await fetch('/api/data-export/data-sources');
            const data = await response.json();
            this.dataSources = data.data_sources;
            
            // Get record counts for each data source
            for (const source of this.dataSources) {
                try {
                    const countResponse = await fetch(`/api/data-export/filter-options?data_source=${source.name}`);
                    const countData = await countResponse.json();
                    source.estimated_records = this.estimateRecordCount(source.name);
                } catch (error) {
                    source.estimated_records = 'Unknown';
                }
            }
        } catch (error) {
            console.error('Failed to load data sources:', error);
            throw error;
        }
    }

    estimateRecordCount(sourceName) {
        // Placeholder for record count estimation
        const estimates = {
            'form_changes': '50,000+',
            'agencies': '500+',
            'forms': '2,000+',
            'monitoring_runs': '100,000+',
            'notifications': '25,000+'
        };
        return estimates[sourceName] || 'Unknown';
    }

    async loadActiveJobs() {
        try {
            // Load jobs from localStorage for persistence
            const savedJobs = localStorage.getItem('bulkExportJobs');
            if (savedJobs) {
                this.activeJobs = JSON.parse(savedJobs);
            }
            
            // Update status for saved jobs
            for (const job of this.activeJobs) {
                if (job.status === 'processing' || job.status === 'pending') {
                    await this.updateJobStatus(job.job_id);
                }
            }
        } catch (error) {
            console.error('Failed to load active jobs:', error);
            this.activeJobs = [];
        }
    }

    renderDataSources() {
        const container = document.getElementById('dataSources');
        container.innerHTML = '';

        this.dataSources.forEach(source => {
            const sourceCard = document.createElement('div');
            sourceCard.className = 'source-card';
            sourceCard.onclick = () => this.toggleDataSource(source.name);
            
            sourceCard.innerHTML = `
                <div class="source-header">
                    <span class="source-title">${source.description}</span>
                    <span class="record-count">${source.estimated_records} records</span>
                </div>
                <div style="color: #6c757d; font-size: 14px;">
                    ${source.available_columns.length} columns available
                </div>
                <div style="margin-top: 10px; font-size: 12px; color: #6c757d;">
                    Columns: ${source.available_columns.slice(0, 5).join(', ')}${source.available_columns.length > 5 ? '...' : ''}
                </div>
            `;

            container.appendChild(sourceCard);
        });
    }

    toggleDataSource(sourceName) {
        const sourceCard = event.currentTarget;
        const isSelected = this.selectedSources.includes(sourceName);

        if (isSelected) {
            this.selectedSources = this.selectedSources.filter(s => s !== sourceName);
            sourceCard.classList.remove('selected');
        } else {
            this.selectedSources.push(sourceName);
            sourceCard.classList.add('selected');
        }

        // Update next button state
        const nextButton = document.querySelector('#step1 .btn-primary');
        nextButton.disabled = this.selectedSources.length === 0;
        nextButton.textContent = this.selectedSources.length === 0 
            ? 'Select at least one data source' 
            : `Next: Configuration (${this.selectedSources.length} selected)`;
    }

    nextStep() {
        if (this.currentStep === 1 && this.selectedSources.length === 0) {
            this.showAlert('Please select at least one data source to export.', 'warning');
            return;
        }

        this.currentStep++;
        this.updateWizardDisplay();

        if (this.currentStep === 3) {
            this.generateExportSummary();
        }
    }

    prevStep() {
        this.currentStep--;
        this.updateWizardDisplay();
    }

    updateWizardDisplay() {
        // Update step indicators
        document.querySelectorAll('.step').forEach((step, index) => {
            const stepNumber = index + 1;
            step.classList.remove('active', 'completed');
            
            if (stepNumber === this.currentStep) {
                step.classList.add('active');
            } else if (stepNumber < this.currentStep) {
                step.classList.add('completed');
            }
        });

        // Show/hide step content
        document.querySelectorAll('.wizard-step').forEach((step, index) => {
            const stepNumber = index + 1;
            step.classList.toggle('hidden', stepNumber !== this.currentStep);
        });
    }

    generateExportSummary() {
        const container = document.getElementById('exportSummary');
        const format = document.getElementById('exportFormat').value;
        const combinedOutput = document.getElementById('combinedOutput').checked;
        const chunkSize = document.getElementById('chunkSize').value;
        const maxRecordsPerFile = document.getElementById('maxRecordsPerFile').value;
        const useStreaming = document.getElementById('useStreaming').checked;
        const notificationEmail = document.getElementById('notificationEmail').value;

        const selectedSourcesInfo = this.selectedSources.map(sourceName => {
            const source = this.dataSources.find(s => s.name === sourceName);
            return {
                name: sourceName,
                description: source ? source.description : sourceName,
                estimated_records: source ? source.estimated_records : 'Unknown'
            };
        });

        container.innerHTML = `
            <div class="config-section">
                <h4>Selected Data Sources (${this.selectedSources.length})</h4>
                ${selectedSourcesInfo.map(source => `
                    <div style="display: flex; justify-content: space-between; padding: 5px 0; border-bottom: 1px solid #e9ecef;">
                        <span>${source.description}</span>
                        <span style="color: #6c757d;">${source.estimated_records} records</span>
                    </div>
                `).join('')}
            </div>

            <div class="config-section">
                <h4>Export Configuration</h4>
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px;">
                    <div><strong>Format:</strong> ${format.toUpperCase()}</div>
                    <div><strong>Combined Output:</strong> ${combinedOutput ? 'Yes' : 'No'}</div>
                    <div><strong>Chunk Size:</strong> ${Number(chunkSize).toLocaleString()} records</div>
                    <div><strong>Max Records/File:</strong> ${Number(maxRecordsPerFile).toLocaleString()}</div>
                    <div><strong>Streaming Mode:</strong> ${useStreaming ? 'Forced' : 'Auto'}</div>
                    <div><strong>Notification:</strong> ${notificationEmail || 'None'}</div>
                </div>
            </div>
        `;

        this.estimateExportSize();
    }

    async estimateExportSize() {
        const sizeElement = document.getElementById('sizeEstimate');
        sizeElement.textContent = 'Calculating...';

        try {
            // Build export requests
            const exportRequests = this.selectedSources.map(sourceName => ({
                data_source: sourceName,
                customization: {
                    format: document.getElementById('exportFormat').value,
                    include_headers: true,
                    include_metadata: true
                }
            }));

            const response = await fetch('/api/data-export/bulk-export', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    exports: exportRequests,
                    combined_output: document.getElementById('combinedOutput').checked
                })
            });

            if (response.ok) {
                const data = await response.json();
                sizeElement.innerHTML = `
                    <strong>${data.estimated_records.toLocaleString()} records</strong> 
                    (~${data.estimated_size_mb.toFixed(1)} MB)
                `;
                
                // Show warning for large exports
                if (data.estimated_size_mb > 100) {
                    sizeElement.parentElement.className = 'alert alert-warning';
                    sizeElement.innerHTML += '<br><small>⚠️ Large export - consider using streaming mode</small>';
                } else {
                    sizeElement.parentElement.className = 'alert alert-success';
                }
            } else {
                throw new Error('Failed to estimate size');
            }
        } catch (error) {
            console.error('Failed to estimate export size:', error);
            sizeElement.textContent = 'Unable to calculate';
            sizeElement.parentElement.className = 'alert alert-error';
        }
    }

    async startExport() {
        const exportButton = document.getElementById('exportButtonText');
        const originalText = exportButton.textContent;
        exportButton.textContent = 'Starting Export...';

        try {
            // Build export configuration
            const exportRequests = this.selectedSources.map(sourceName => ({
                data_source: sourceName,
                customization: {
                    format: document.getElementById('exportFormat').value,
                    include_headers: true,
                    include_metadata: true,
                    include_ai_analysis: true,
                    include_impact_assessment: true
                }
            }));

            const requestBody = {
                exports: exportRequests,
                combined_output: document.getElementById('combinedOutput').checked,
                chunk_size: parseInt(document.getElementById('chunkSize').value),
                use_streaming: document.getElementById('useStreaming').checked
            };

            // Determine if we should use large bulk export endpoint
            const maxRecordsPerFile = parseInt(document.getElementById('maxRecordsPerFile').value);
            const notificationEmail = document.getElementById('notificationEmail').value;
            const compressionLevel = parseInt(document.getElementById('compressionLevel').value);

            let endpoint = '/api/data-export/bulk-export';
            
            if (maxRecordsPerFile !== 100000 || notificationEmail || compressionLevel !== 6) {
                endpoint = '/api/data-export/large-bulk-export';
                requestBody.max_records_per_file = maxRecordsPerFile;
                requestBody.compression_level = compressionLevel;
                if (notificationEmail) {
                    requestBody.notification_email = notificationEmail;
                }
            }

            const response = await fetch(endpoint, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(requestBody)
            });

            if (response.ok) {
                const data = await response.json();
                this.currentJobId = data.job_id;
                
                // Save job to localStorage
                const jobInfo = {
                    job_id: data.job_id,
                    status: data.status,
                    estimated_records: data.estimated_records,
                    estimated_size_mb: data.estimated_size_mb,
                    created_at: data.created_at,
                    expires_at: data.expires_at,
                    data_sources: this.selectedSources
                };
                
                this.activeJobs.unshift(jobInfo);
                this.saveJobsToStorage();

                // Hide wizard and show progress
                document.getElementById('exportWizard').style.display = 'none';
                document.getElementById('progressContainer').style.display = 'block';

                // Start progress tracking
                this.startProgressTracking();
                this.renderActiveJobs();
                
                this.showAlert(`Export job ${data.job_id} started successfully!`, 'success');
            } else {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Failed to start export');
            }
        } catch (error) {
            console.error('Failed to start export:', error);
            this.showAlert(`Failed to start export: ${error.message}`, 'error');
        } finally {
            exportButton.textContent = originalText;
        }
    }

    startProgressTracking() {
        if (this.progressInterval) {
            clearInterval(this.progressInterval);
        }

        this.progressInterval = setInterval(async () => {
            if (this.currentJobId) {
                await this.updateProgressDisplay();
            }
        }, 2000); // Update every 2 seconds
    }

    async updateProgressDisplay() {
        try {
            const response = await fetch(`/api/data-export/bulk-export/${this.currentJobId}/detailed-status`);
            
            if (response.ok) {
                const job = await response.json();
                this.updateProgressUI(job);
                
                // Update job in storage
                const jobIndex = this.activeJobs.findIndex(j => j.job_id === this.currentJobId);
                if (jobIndex !== -1) {
                    this.activeJobs[jobIndex] = { ...this.activeJobs[jobIndex], ...job };
                    this.saveJobsToStorage();
                }

                // Stop tracking if job is completed or failed
                if (job.status === 'completed' || job.status === 'failed' || job.status === 'cancelled') {
                    clearInterval(this.progressInterval);
                    this.progressInterval = null;
                    
                    if (job.status === 'completed') {
                        this.showExportResult(job);
                    } else if (job.status === 'failed') {
                        this.showAlert(`Export failed: ${job.error_message}`, 'error');
                    }
                }
            } else {
                console.error('Failed to fetch job status');
            }
        } catch (error) {
            console.error('Error updating progress:', error);
        }
    }

    updateProgressUI(job) {
        document.getElementById('progressFill').style.width = `${job.progress_percent}%`;
        document.getElementById('progressText').textContent = `${job.progress_percent}% Complete`;
        
        document.getElementById('recordsProcessed').textContent = job.processed_records.toLocaleString();
        document.getElementById('totalRecords').textContent = job.total_records.toLocaleString();
        document.getElementById('currentChunk').textContent = job.current_chunk;
        
        if (job.processing_rate_records_per_second) {
            document.getElementById('processingRate').textContent = 
                Math.round(job.processing_rate_records_per_second).toLocaleString();
        }
    }

    showExportResult(job) {
        const resultContainer = document.getElementById('exportResult');
        resultContainer.className = 'alert alert-success';
        resultContainer.innerHTML = `
            <h4>Export Completed Successfully!</h4>
            <p><strong>Job ID:</strong> ${job.job_id}</p>
            <p><strong>Records Exported:</strong> ${job.total_records.toLocaleString()}</p>
            <p><strong>File Size:</strong> ${(job.file_size_bytes / 1024 / 1024).toFixed(2)} MB</p>
            <p><strong>Processing Time:</strong> ${job.runtime_seconds ? Math.round(job.runtime_seconds / 60) : 'N/A'} minutes</p>
            ${job.download_url ? `
                <a href="${job.download_url}" class="btn btn-primary" download>
                    Download Export File
                </a>
            ` : ''}
            <button class="btn btn-secondary" onclick="bulkExportManager.resetWizard()" style="margin-left: 10px;">
                Start New Export
            </button>
        `;
        resultContainer.classList.remove('hidden');
        
        // Hide cancel button
        document.getElementById('cancelButton').style.display = 'none';
    }

    async cancelExport() {
        if (!this.currentJobId) return;

        if (confirm('Are you sure you want to cancel this export?')) {
            try {
                const response = await fetch(`/api/data-export/bulk-export/${this.currentJobId}/cancel`, {
                    method: 'POST'
                });

                if (response.ok) {
                    clearInterval(this.progressInterval);
                    this.progressInterval = null;
                    this.showAlert('Export cancelled successfully.', 'warning');
                    this.resetWizard();
                } else {
                    throw new Error('Failed to cancel export');
                }
            } catch (error) {
                console.error('Failed to cancel export:', error);
                this.showAlert('Failed to cancel export.', 'error');
            }
        }
    }

    resetWizard() {
        this.currentStep = 1;
        this.selectedSources = [];
        this.currentJobId = null;
        
        if (this.progressInterval) {
            clearInterval(this.progressInterval);
            this.progressInterval = null;
        }

        document.getElementById('exportWizard').style.display = 'block';
        document.getElementById('progressContainer').style.display = 'none';
        document.getElementById('exportResult').classList.add('hidden');
        document.getElementById('cancelButton').style.display = 'block';

        this.updateWizardDisplay();
        this.renderDataSources();
        this.renderActiveJobs();
    }

    async updateJobStatus(jobId) {
        try {
            const response = await fetch(`/api/data-export/export/${jobId}/status`);
            if (response.ok) {
                const job = await response.json();
                const jobIndex = this.activeJobs.findIndex(j => j.job_id === jobId);
                if (jobIndex !== -1) {
                    this.activeJobs[jobIndex] = { ...this.activeJobs[jobIndex], ...job };
                }
            }
        } catch (error) {
            console.error(`Failed to update status for job ${jobId}:`, error);
        }
    }

    renderActiveJobs() {
        const container = document.getElementById('jobsList');
        
        if (this.activeJobs.length === 0) {
            container.innerHTML = `
                <div style="padding: 40px; text-align: center; color: #6c757d;">
                    No export jobs found. Create your first bulk export above.
                </div>
            `;
            return;
        }

        container.innerHTML = this.activeJobs.map(job => {
            const createdAt = new Date(job.created_at).toLocaleString();
            const statusClass = `status-${job.status}`;
            
            return `
                <div class="job-item">
                    <div class="job-info">
                        <div class="job-id">${job.job_id}</div>
                        <div class="job-details">
                            Created: ${createdAt} | 
                            Records: ${job.estimated_records ? job.estimated_records.toLocaleString() : 'Unknown'} |
                            Sources: ${job.data_sources ? job.data_sources.length : 'Unknown'}
                        </div>
                    </div>
                    <div class="job-status ${statusClass}">${job.status}</div>
                    <div class="job-actions">
                        ${job.status === 'completed' && job.download_url ? `
                            <a href="${job.download_url}" class="btn btn-primary" download>Download</a>
                        ` : ''}
                        ${job.status === 'processing' || job.status === 'pending' ? `
                            <button class="btn btn-secondary" onclick="bulkExportManager.trackJob('${job.job_id}')">
                                Track Progress
                            </button>
                            <button class="btn btn-danger" onclick="bulkExportManager.cancelJobById('${job.job_id}')">
                                Cancel
                            </button>
                        ` : ''}
                        <button class="btn btn-secondary" onclick="bulkExportManager.removeJob('${job.job_id}')">
                            Remove
                        </button>
                    </div>
                </div>
            `;
        }).join('');
    }

    async trackJob(jobId) {
        this.currentJobId = jobId;
        document.getElementById('exportWizard').style.display = 'none';
        document.getElementById('progressContainer').style.display = 'block';
        this.startProgressTracking();
    }

    async cancelJobById(jobId) {
        if (confirm('Are you sure you want to cancel this export?')) {
            try {
                const response = await fetch(`/api/data-export/bulk-export/${jobId}/cancel`, {
                    method: 'POST'
                });

                if (response.ok) {
                    this.showAlert('Export cancelled successfully.', 'warning');
                    await this.loadActiveJobs();
                    this.renderActiveJobs();
                } else {
                    throw new Error('Failed to cancel export');
                }
            } catch (error) {
                console.error('Failed to cancel export:', error);
                this.showAlert('Failed to cancel export.', 'error');
            }
        }
    }

    removeJob(jobId) {
        this.activeJobs = this.activeJobs.filter(job => job.job_id !== jobId);
        this.saveJobsToStorage();
        this.renderActiveJobs();
    }

    async refreshJobs() {
        try {
            await this.loadActiveJobs();
            this.renderActiveJobs();
            this.showAlert('Jobs list refreshed.', 'success');
        } catch (error) {
            console.error('Failed to refresh jobs:', error);
            this.showAlert('Failed to refresh jobs list.', 'error');
        }
    }

    saveJobsToStorage() {
        try {
            localStorage.setItem('bulkExportJobs', JSON.stringify(this.activeJobs));
        } catch (error) {
            console.error('Failed to save jobs to storage:', error);
        }
    }

    showAlert(message, type = 'info') {
        const alertClass = `alert-${type === 'info' ? 'success' : type}`;
        const alertHtml = `
            <div class="alert ${alertClass}" style="position: fixed; top: 20px; right: 20px; z-index: 1000; max-width: 400px;">
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
function nextStep() {
    bulkExportManager.nextStep();
}

function prevStep() {
    bulkExportManager.prevStep();
}

function startExport() {
    bulkExportManager.startExport();
}

function cancelExport() {
    bulkExportManager.cancelExport();
}

function refreshJobs() {
    bulkExportManager.refreshJobs();
}

// Initialize the bulk export manager when the page loads
let bulkExportManager;
document.addEventListener('DOMContentLoaded', () => {
    bulkExportManager = new BulkExportManager();
});