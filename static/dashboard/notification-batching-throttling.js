/**
 * Notification Batching & Throttling Interface JavaScript
 *
 * This file provides the frontend functionality for managing notification
 * batching and throttling configuration and monitoring.
 */

// Global variables
let currentConfig = {
    batching: {},
    throttling: {}
};

// API base URL
const API_BASE = '/api/notification-batching-throttling';

// Initialize the interface
document.addEventListener('DOMContentLoaded', function() {
    initializeInterface();
    loadInitialData();
    setupEventListeners();
});

/**
 * Initialize the interface components
 */
async function initializeInterface() {
    console.log('Initializing notification batching & throttling interface...');
    
    // Load configurations
    await loadBatchingConfig();
    await loadThrottlingConfig();
    
    // Load system status
    await loadSystemStatus();
    
    // Load monitoring data
    await loadMonitoringData();
}

/**
 * Load initial data
 */
async function loadInitialData() {
    try {
        showLoading();
        
        // Load all data in parallel
        await Promise.all([
            loadBatchingConfig(),
            loadThrottlingConfig(),
            loadSystemStatus(),
            loadMonitoringData()
        ]);
        
        hideLoading();
    } catch (error) {
        console.error('Error loading initial data:', error);
        showError('Failed to load initial data');
        hideLoading();
    }
}

/**
 * Set up event listeners
 */
function setupEventListeners() {
    // Auto-refresh monitoring data every 30 seconds
    setInterval(loadMonitoringData, 30000);
}

/**
 * Load batching configuration
 */
async function loadBatchingConfig() {
    try {
        const response = await fetch(`${API_BASE}/config/batching`, {
            headers: getAuthHeaders()
        });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        
        if (data.status === 'success') {
            currentConfig.batching = data.data;
            populateBatchingConfig(data.data);
        }
    } catch (error) {
        console.error('Error loading batching config:', error);
        showError('Failed to load batching configuration');
    }
}

/**
 * Populate batching configuration in the UI
 */
function populateBatchingConfig(config) {
    document.getElementById('batchingEnabled').checked = config.enabled;
    document.getElementById('maxBatchSize').value = config.max_batch_size;
    document.getElementById('maxBatchDelay').value = config.max_batch_delay_minutes;
    document.getElementById('priorityOverride').checked = config.priority_override;
    document.getElementById('groupByUser').checked = config.group_by_user;
    document.getElementById('groupBySeverity').checked = config.group_by_severity;
    document.getElementById('groupByChannel').checked = config.group_by_channel;
    
    // Update status indicator
    const statusIndicator = document.getElementById('batchingStatus');
    statusIndicator.className = `status-indicator ${config.enabled ? 'status-enabled' : 'status-disabled'}`;
}

/**
 * Save batching configuration
 */
async function saveBatchingConfig() {
    try {
        const configData = {
            enabled: document.getElementById('batchingEnabled').checked,
            max_batch_size: parseInt(document.getElementById('maxBatchSize').value),
            max_batch_delay_minutes: parseInt(document.getElementById('maxBatchDelay').value),
            priority_override: document.getElementById('priorityOverride').checked,
            group_by_user: document.getElementById('groupByUser').checked,
            group_by_severity: document.getElementById('groupBySeverity').checked,
            group_by_channel: document.getElementById('groupByChannel').checked
        };
        
        const response = await fetch(`${API_BASE}/config/batching`, {
            method: 'PUT',
            headers: {
                ...getAuthHeaders(),
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(configData)
        });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        
        if (data.status === 'success') {
            showSuccess('Batching configuration saved successfully');
            currentConfig.batching = data.data;
        }
    } catch (error) {
        console.error('Error saving batching config:', error);
        showError('Failed to save batching configuration');
    }
}

/**
 * Load throttling configuration
 */
async function loadThrottlingConfig() {
    try {
        const response = await fetch(`${API_BASE}/config/throttling`, {
            headers: getAuthHeaders()
        });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        
        if (data.status === 'success') {
            currentConfig.throttling = data.data;
            populateThrottlingConfig(data.data);
        }
    } catch (error) {
        console.error('Error loading throttling config:', error);
        showError('Failed to load throttling configuration');
    }
}

/**
 * Populate throttling configuration in the UI
 */
function populateThrottlingConfig(config) {
    document.getElementById('throttlingEnabled').checked = config.enabled;
    document.getElementById('rateLimitHour').value = config.rate_limit_per_hour;
    document.getElementById('rateLimitDay').value = config.rate_limit_per_day;
    document.getElementById('cooldownMinutes').value = config.cooldown_minutes;
    document.getElementById('burstLimit').value = config.burst_limit;
    document.getElementById('burstWindow').value = config.burst_window_minutes;
    document.getElementById('exemptHighPriority').checked = config.exempt_high_priority;
    document.getElementById('exemptCritical').checked = config.exempt_critical_severity;
    
    // Update status indicator
    const statusIndicator = document.getElementById('throttlingStatus');
    statusIndicator.className = `status-indicator ${config.enabled ? 'status-enabled' : 'status-disabled'}`;
}

/**
 * Save throttling configuration
 */
async function saveThrottlingConfig() {
    try {
        const configData = {
            enabled: document.getElementById('throttlingEnabled').checked,
            rate_limit_per_hour: parseInt(document.getElementById('rateLimitHour').value),
            rate_limit_per_day: parseInt(document.getElementById('rateLimitDay').value),
            cooldown_minutes: parseInt(document.getElementById('cooldownMinutes').value),
            burst_limit: parseInt(document.getElementById('burstLimit').value),
            burst_window_minutes: parseInt(document.getElementById('burstWindow').value),
            exempt_high_priority: document.getElementById('exemptHighPriority').checked,
            exempt_critical_severity: document.getElementById('exemptCritical').checked
        };
        
        const response = await fetch(`${API_BASE}/config/throttling`, {
            method: 'PUT',
            headers: {
                ...getAuthHeaders(),
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(configData)
        });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        
        if (data.status === 'success') {
            showSuccess('Throttling configuration saved successfully');
            currentConfig.throttling = data.data;
        }
    } catch (error) {
        console.error('Error saving throttling config:', error);
        showError('Failed to save throttling configuration');
    }
}

/**
 * Load system status
 */
async function loadSystemStatus() {
    try {
        const response = await fetch(`${API_BASE}/status`, {
            headers: getAuthHeaders()
        });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        
        if (data.status === 'success') {
            updateSystemStatus(data.data);
        }
    } catch (error) {
        console.error('Error loading system status:', error);
        showError('Failed to load system status');
    }
}

/**
 * Update system status display
 */
function updateSystemStatus(status) {
    // Update status indicators
    const batchingStatus = document.getElementById('batchingStatus');
    const throttlingStatus = document.getElementById('throttlingStatus');
    
    batchingStatus.className = `status-indicator ${status.batching.enabled ? 'status-enabled' : 'status-disabled'}`;
    throttlingStatus.className = `status-indicator ${status.throttling.enabled ? 'status-enabled' : 'status-disabled'}`;
}

/**
 * Load monitoring data
 */
async function loadMonitoringData() {
    try {
        // Load analytics summary
        const analyticsResponse = await fetch(`${API_BASE}/analytics/summary`, {
            headers: getAuthHeaders()
        });
        
        if (analyticsResponse.ok) {
            const analyticsData = await analyticsResponse.json();
            if (analyticsData.status === 'success') {
                updateMonitoringMetrics(analyticsData.data);
            }
        }
        
        // Load active batches
        const batchesResponse = await fetch(`${API_BASE}/batches`, {
            headers: getAuthHeaders()
        });
        
        if (batchesResponse.ok) {
            const batchesData = await batchesResponse.json();
            if (batchesData.status === 'success') {
                updateBatchesTable(batchesData.data.active_batches);
            }
        }
    } catch (error) {
        console.error('Error loading monitoring data:', error);
        // Don't show error for monitoring data as it's auto-refreshed
    }
}

/**
 * Update monitoring metrics
 */
function updateMonitoringMetrics(data) {
    document.getElementById('activeBatches').textContent = data.active_batches;
    document.getElementById('trackedUsers').textContent = data.active_throttle_metrics;
    document.getElementById('recentBatched').textContent = data.recent_notifications.batched;
    document.getElementById('recentThrottled').textContent = data.recent_notifications.throttled;
}

/**
 * Update batches table
 */
function updateBatchesTable(batches) {
    const tbody = document.getElementById('batchesTableBody');
    tbody.innerHTML = '';
    
    if (batches.length === 0) {
        tbody.innerHTML = '<tr><td colspan="9" style="text-align: center; color: #666;">No active batches</td></tr>';
        return;
    }
    
    batches.forEach(batch => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${batch.id}</td>
            <td>${batch.user_id}</td>
            <td>${batch.channel}</td>
            <td><span class="severity-badge severity-${batch.severity}">${batch.severity}</span></td>
            <td>${batch.notifications_count}</td>
            <td>${batch.priority_score.toFixed(1)}</td>
            <td>${formatDateTime(batch.created_at)}</td>
            <td>${formatDateTime(batch.estimated_send_time)}</td>
            <td>
                <div class="batch-actions">
                    <button class="action-button send" onclick="sendBatch('${batch.id}')">
                        <i class="fas fa-paper-plane"></i> Send
                    </button>
                    <button class="action-button cancel" onclick="cancelBatch('${batch.id}')">
                        <i class="fas fa-times"></i> Cancel
                    </button>
                </div>
            </td>
        `;
        tbody.appendChild(row);
    });
}

/**
 * Send batch immediately
 */
async function sendBatch(batchId) {
    try {
        const response = await fetch(`${API_BASE}/batches/${batchId}/send`, {
            method: 'POST',
            headers: getAuthHeaders()
        });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        
        if (data.status === 'success') {
            showSuccess(`Batch ${batchId} sent successfully`);
            await loadMonitoringData(); // Refresh data
        }
    } catch (error) {
        console.error('Error sending batch:', error);
        showError('Failed to send batch');
    }
}

/**
 * Cancel batch
 */
async function cancelBatch(batchId) {
    if (!confirm(`Are you sure you want to cancel batch ${batchId}?`)) {
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE}/batches/${batchId}`, {
            method: 'DELETE',
            headers: getAuthHeaders()
        });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        
        if (data.status === 'success') {
            showSuccess(`Batch ${batchId} cancelled successfully`);
            await loadMonitoringData(); // Refresh data
        }
    } catch (error) {
        console.error('Error cancelling batch:', error);
        showError('Failed to cancel batch');
    }
}

/**
 * Test notification processing
 */
async function testNotification() {
    try {
        const notificationData = {
            subject: document.getElementById('testSubject').value,
            message: document.getElementById('testMessage').value,
            severity: document.getElementById('testSeverity').value,
            channel: 'email'
        };
        
        const response = await fetch(`${API_BASE}/test/notification`, {
            method: 'POST',
            headers: {
                ...getAuthHeaders(),
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(notificationData)
        });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        
        if (data.status === 'success') {
            displayTestResult(data.data);
            showSuccess('Notification test completed successfully');
        }
    } catch (error) {
        console.error('Error testing notification:', error);
        showError('Failed to test notification');
    }
}

/**
 * Display test result
 */
function displayTestResult(result) {
    const testResultDiv = document.getElementById('testResult');
    
    const resultHtml = `
        <h4>Test Result</h4>
        <div style="margin-bottom: 15px;">
            <strong>Status:</strong> ${result.processing_result.status}<br>
            <strong>Batch ID:</strong> ${result.processing_result.batch_id || 'N/A'}<br>
            <strong>Throttled:</strong> ${result.processing_result.throttled ? 'Yes' : 'No'}<br>
            ${result.processing_result.reason ? `<strong>Reason:</strong> ${result.processing_result.reason}<br>` : ''}
        </div>
        <div>
            <strong>Notification Data:</strong><br>
            <pre style="background: #f1f1f1; padding: 10px; border-radius: 5px; font-size: 12px;">${JSON.stringify(result.notification_data, null, 2)}</pre>
        </div>
    `;
    
    testResultDiv.innerHTML = resultHtml;
    testResultDiv.style.display = 'block';
}

/**
 * Refresh all data
 */
async function refreshData() {
    try {
        showLoading();
        await loadInitialData();
        hideLoading();
        showSuccess('Data refreshed successfully');
    } catch (error) {
        console.error('Error refreshing data:', error);
        showError('Failed to refresh data');
        hideLoading();
    }
}

/**
 * Show loading indicator
 */
function showLoading() {
    document.getElementById('loadingIndicator').style.display = 'block';
}

/**
 * Hide loading indicator
 */
function hideLoading() {
    document.getElementById('loadingIndicator').style.display = 'none';
}

/**
 * Get authentication headers
 */
function getAuthToken() {
    // Get token from localStorage or sessionStorage
    return localStorage.getItem('authToken') || sessionStorage.getItem('authToken');
}

/**
 * Get authentication headers
 */
function getAuthHeaders() {
    const token = getAuthToken();
    return {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
    };
}

/**
 * Show success message
 */
function showSuccess(message) {
    const alertContainer = document.getElementById('alertContainer');
    alertContainer.innerHTML = `
        <div class="alert success">
            <i class="fas fa-check-circle"></i> ${message}
        </div>
    `;
    alertContainer.style.display = 'block';
    
    // Auto-hide after 5 seconds
    setTimeout(() => {
        alertContainer.style.display = 'none';
    }, 5000);
}

/**
 * Show error message
 */
function showError(message) {
    const alertContainer = document.getElementById('alertContainer');
    alertContainer.innerHTML = `
        <div class="alert error">
            <i class="fas fa-exclamation-circle"></i> ${message}
        </div>
    `;
    alertContainer.style.display = 'block';
    
    // Auto-hide after 10 seconds
    setTimeout(() => {
        alertContainer.style.display = 'none';
    }, 10000);
}

/**
 * Format date time
 */
function formatDateTime(dateTimeString) {
    if (!dateTimeString) return 'N/A';
    
    const date = new Date(dateTimeString);
    return date.toLocaleString();
} 