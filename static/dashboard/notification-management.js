/**
 * Notification Management Interface JavaScript
 * 
 * This file provides the frontend functionality for the notification management interface,
 * including data loading, filtering, searching, bulk operations, and analytics.
 */

// Global variables
let currentPage = 1;
let currentPageSize = 50;
let currentFilters = {};
let currentSearchTerm = '';
let selectedNotifications = new Set();
let charts = {};

// API base URL
const API_BASE = '/api/notification-management';

// Initialize the interface
document.addEventListener('DOMContentLoaded', function() {
    initializeInterface();
    loadInitialData();
});

/**
 * Initialize the interface components
 */
async function initializeInterface() {
    try {
        // Load filter options
        await loadFilterOptions();
        
        // Set up event listeners
        setupEventListeners();
        
        // Initialize charts
        initializeCharts();
        
    } catch (error) {
        console.error('Error initializing interface:', error);
        showError('Failed to initialize interface');
    }
}

/**
 * Load initial data
 */
async function loadInitialData() {
    try {
        // Load summary statistics
        await loadSummaryStats();
        
        // Load notification history
        await loadNotificationHistory();
        
    } catch (error) {
        console.error('Error loading initial data:', error);
        showError('Failed to load initial data');
    }
}

/**
 * Load filter options from the API
 */
async function loadFilterOptions() {
    try {
        const response = await fetch(`${API_BASE}/filters/options`);
        const data = await response.json();
        
        if (data.success) {
            populateFilterOptions(data.data);
        } else {
            throw new Error('Failed to load filter options');
        }
    } catch (error) {
        console.error('Error loading filter options:', error);
        showError('Failed to load filter options');
    }
}

/**
 * Populate filter dropdowns with options
 */
function populateFilterOptions(options) {
    // Status filter
    const statusFilter = document.getElementById('statusFilter');
    options.statuses.forEach(status => {
        const option = document.createElement('option');
        option.value = status;
        option.textContent = status.charAt(0).toUpperCase() + status.slice(1);
        statusFilter.appendChild(option);
    });
    
    // Notification type filter
    const typeFilter = document.getElementById('typeFilter');
    options.notification_types.forEach(type => {
        const option = document.createElement('option');
        option.value = type;
        option.textContent = type.charAt(0).toUpperCase() + type.slice(1);
        typeFilter.appendChild(option);
    });
    
    // Severity filter
    const severityFilter = document.getElementById('severityFilter');
    options.severities.forEach(severity => {
        const option = document.createElement('option');
        option.value = severity;
        option.textContent = severity.charAt(0).toUpperCase() + severity.slice(1);
        severityFilter.appendChild(option);
    });
}

/**
 * Set up event listeners
 */
function setupEventListeners() {
    // Search input enter key
    document.getElementById('searchInput').addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            performSearch();
        }
    });
    
    // Filter inputs
    document.getElementById('recipientFilter').addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            applyFilters();
        }
    });
}

/**
 * Load summary statistics
 */
async function loadSummaryStats() {
    try {
        const response = await fetch(`${API_BASE}/stats/summary`);
        const data = await response.json();
        
        if (data.success) {
            updateSummaryStats(data.data);
        } else {
            throw new Error('Failed to load summary statistics');
        }
    } catch (error) {
        console.error('Error loading summary stats:', error);
        showError('Failed to load summary statistics');
    }
}

/**
 * Update summary statistics display
 */
function updateSummaryStats(stats) {
    document.getElementById('totalNotifications').textContent = stats.total_notifications || 0;
    document.getElementById('pendingCount').textContent = stats.pending_count || 0;
    document.getElementById('failedCount').textContent = stats.failed_count || 0;
    document.getElementById('recentCount').textContent = stats.recent_24h_count || 0;
}

/**
 * Load notification history
 */
async function loadNotificationHistory() {
    try {
        showLoading();
        
        const params = new URLSearchParams({
            page: currentPage,
            page_size: currentPageSize,
            sort_by: 'sent_at',
            sort_order: 'desc',
            ...currentFilters
        });
        
        const response = await fetch(`${API_BASE}/history?${params}`);
        const data = await response.json();
        
        if (data.success) {
            displayNotifications(data.data);
        } else {
            throw new Error('Failed to load notification history');
        }
    } catch (error) {
        console.error('Error loading notification history:', error);
        showError('Failed to load notification history');
    }
}

/**
 * Display notifications in the table
 */
function displayNotifications(data) {
    const tbody = document.getElementById('notificationsTableBody');
    const notifications = data.notifications;
    
    if (notifications.length === 0) {
        tbody.innerHTML = '<tr><td colspan="9" class="loading">No notifications found</td></tr>';
        return;
    }
    
    tbody.innerHTML = notifications.map(notification => `
        <tr>
            <td>
                <input type="checkbox" value="${notification.id}" onchange="toggleNotificationSelection(${notification.id})">
            </td>
            <td>${notification.id}</td>
            <td>${notification.notification_type}</td>
            <td>${notification.recipient}</td>
            <td>${notification.subject || '-'}</td>
            <td>
                <span class="status-badge status-${notification.status}">
                    ${notification.status}
                </span>
            </td>
            <td>${formatDateTime(notification.sent_at)}</td>
            <td>${notification.retry_count}</td>
            <td>
                <div class="action-buttons">
                    <button class="action-btn btn-primary" onclick="viewNotificationDetails(${notification.id})">
                        <i class="fas fa-eye"></i>
                    </button>
                    ${notification.status === 'failed' ? `
                        <button class="action-btn btn-success" onclick="resendNotification(${notification.id})">
                            <i class="fas fa-redo"></i>
                        </button>
                    ` : ''}
                    ${notification.status === 'pending' || notification.status === 'retrying' ? `
                        <button class="action-btn btn-danger" onclick="cancelNotification(${notification.id})">
                            <i class="fas fa-times"></i>
                        </button>
                    ` : ''}
                </div>
            </td>
        </tr>
    `).join('');
    
    // Update pagination
    updatePagination(data.pagination);
}

/**
 * Update pagination controls
 */
function updatePagination(pagination) {
    const paginationContainer = document.getElementById('pagination');
    
    let paginationHTML = '';
    
    // Previous button
    paginationHTML += `
        <button onclick="changePage(${pagination.page - 1})" ${!pagination.has_prev ? 'disabled' : ''}>
            <i class="fas fa-chevron-left"></i> Previous
        </button>
    `;
    
    // Page numbers
    const startPage = Math.max(1, pagination.page - 2);
    const endPage = Math.min(pagination.total_pages, pagination.page + 2);
    
    for (let i = startPage; i <= endPage; i++) {
        paginationHTML += `
            <button onclick="changePage(${i})" class="${i === pagination.page ? 'current-page' : ''}">
                ${i}
            </button>
        `;
    }
    
    // Next button
    paginationHTML += `
        <button onclick="changePage(${pagination.page + 1})" ${!pagination.has_next ? 'disabled' : ''}>
            Next <i class="fas fa-chevron-right"></i>
        </button>
    `;
    
    paginationContainer.innerHTML = paginationHTML;
}

/**
 * Change page
 */
function changePage(page) {
    currentPage = page;
    loadNotificationHistory();
}

/**
 * Apply filters
 */
function applyFilters() {
    currentFilters = {};
    
    const status = document.getElementById('statusFilter').value;
    const type = document.getElementById('typeFilter').value;
    const recipient = document.getElementById('recipientFilter').value;
    const startDate = document.getElementById('startDateFilter').value;
    const endDate = document.getElementById('endDateFilter').value;
    const severity = document.getElementById('severityFilter').value;
    
    if (status) currentFilters.status = status;
    if (type) currentFilters.notification_type = type;
    if (recipient) currentFilters.recipient = recipient;
    if (startDate) currentFilters.start_date = startDate;
    if (endDate) currentFilters.end_date = endDate;
    if (severity) currentFilters.severity = severity;
    
    currentPage = 1;
    loadNotificationHistory();
}

/**
 * Clear filters
 */
function clearFilters() {
    document.getElementById('statusFilter').value = '';
    document.getElementById('typeFilter').value = '';
    document.getElementById('recipientFilter').value = '';
    document.getElementById('startDateFilter').value = '';
    document.getElementById('endDateFilter').value = '';
    document.getElementById('severityFilter').value = '';
    
    currentFilters = {};
    currentPage = 1;
    loadNotificationHistory();
}

/**
 * Perform search
 */
async function performSearch() {
    const searchTerm = document.getElementById('searchInput').value.trim();
    
    if (!searchTerm) {
        clearSearch();
        return;
    }
    
    try {
        showLoading();
        
        const params = new URLSearchParams({
            search_term: searchTerm,
            page: 1,
            page_size: currentPageSize
        });
        
        const response = await fetch(`${API_BASE}/search?${params}`);
        const data = await response.json();
        
        if (data.success) {
            currentSearchTerm = searchTerm;
            displayNotifications(data.data);
        } else {
            throw new Error('Search failed');
        }
    } catch (error) {
        console.error('Error performing search:', error);
        showError('Search failed');
    }
}

/**
 * Clear search
 */
function clearSearch() {
    document.getElementById('searchInput').value = '';
    currentSearchTerm = '';
    loadNotificationHistory();
}

/**
 * Toggle notification selection
 */
function toggleNotificationSelection(notificationId) {
    if (selectedNotifications.has(notificationId)) {
        selectedNotifications.delete(notificationId);
    } else {
        selectedNotifications.add(notificationId);
    }
    
    updateSelectAllCheckbox();
}

/**
 * Toggle select all
 */
function toggleSelectAll() {
    const selectAllCheckbox = document.getElementById('selectAll');
    const checkboxes = document.querySelectorAll('#notificationsTableBody input[type="checkbox"]');
    
    if (selectAllCheckbox.checked) {
        checkboxes.forEach(checkbox => {
            checkbox.checked = true;
            selectedNotifications.add(parseInt(checkbox.value));
        });
    } else {
        checkboxes.forEach(checkbox => {
            checkbox.checked = false;
            selectedNotifications.delete(parseInt(checkbox.value));
        });
    }
}

/**
 * Update select all checkbox state
 */
function updateSelectAllCheckbox() {
    const selectAllCheckbox = document.getElementById('selectAll');
    const checkboxes = document.querySelectorAll('#notificationsTableBody input[type="checkbox"]');
    const checkedCount = document.querySelectorAll('#notificationsTableBody input[type="checkbox"]:checked').length;
    
    selectAllCheckbox.checked = checkedCount === checkboxes.length && checkboxes.length > 0;
    selectAllCheckbox.indeterminate = checkedCount > 0 && checkedCount < checkboxes.length;
}

/**
 * View notification details
 */
async function viewNotificationDetails(notificationId) {
    try {
        const response = await fetch(`${API_BASE}/notifications/${notificationId}/details`);
        const data = await response.json();
        
        if (data.success) {
            showNotificationDetails(data.data);
        } else {
            throw new Error('Failed to load notification details');
        }
    } catch (error) {
        console.error('Error loading notification details:', error);
        showError('Failed to load notification details');
    }
}

/**
 * Show notification details modal
 */
function showNotificationDetails(details) {
    const modal = document.getElementById('notificationModal');
    const detailsContainer = document.getElementById('notificationDetails');
    
    detailsContainer.innerHTML = `
        <div class="notification-details">
            <h4>Notification Information</h4>
            <p><strong>ID:</strong> ${details.notification.id}</p>
            <p><strong>Type:</strong> ${details.notification.notification_type}</p>
            <p><strong>Recipient:</strong> ${details.notification.recipient}</p>
            <p><strong>Subject:</strong> ${details.notification.subject || 'N/A'}</p>
            <p><strong>Status:</strong> <span class="status-badge status-${details.notification.status}">${details.notification.status}</span></p>
            <p><strong>Sent At:</strong> ${formatDateTime(details.notification.sent_at)}</p>
            <p><strong>Retry Count:</strong> ${details.notification.retry_count}</p>
            <p><strong>Delivery Time:</strong> ${details.notification.delivery_time ? details.notification.delivery_time + 's' : 'N/A'}</p>
            
            ${details.notification.error_message ? `
                <p><strong>Error:</strong> ${details.notification.error_message}</p>
            ` : ''}
            
            ${details.form_change ? `
                <h4>Form Change Information</h4>
                <p><strong>Change Type:</strong> ${details.form_change.change_type}</p>
                <p><strong>Description:</strong> ${details.form_change.change_description}</p>
                <p><strong>Severity:</strong> ${details.form_change.severity}</p>
                <p><strong>Detected At:</strong> ${formatDateTime(details.form_change.detected_at)}</p>
            ` : ''}
            
            ${details.form ? `
                <h4>Form Information</h4>
                <p><strong>Name:</strong> ${details.form.name}</p>
                <p><strong>Title:</strong> ${details.form.title}</p>
            ` : ''}
            
            ${details.agency ? `
                <h4>Agency Information</h4>
                <p><strong>Name:</strong> ${details.agency.name}</p>
                <p><strong>Abbreviation:</strong> ${details.agency.abbreviation}</p>
            ` : ''}
        </div>
    `;
    
    modal.style.display = 'block';
}

/**
 * Resend notification
 */
async function resendNotification(notificationId) {
    if (!confirm('Are you sure you want to resend this notification?')) {
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE}/resend/${notificationId}`, {
            method: 'POST'
        });
        
        const data = await response.json();
        
        if (data.success) {
            showSuccess('Notification resent successfully');
            loadNotificationHistory();
        } else {
            throw new Error(data.detail || 'Failed to resend notification');
        }
    } catch (error) {
        console.error('Error resending notification:', error);
        showError('Failed to resend notification');
    }
}

/**
 * Cancel notification
 */
async function cancelNotification(notificationId) {
    const reason = prompt('Please provide a reason for cancellation (optional):');
    
    try {
        const response = await fetch(`${API_BASE}/cancel/${notificationId}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ reason })
        });
        
        const data = await response.json();
        
        if (data.success) {
            showSuccess('Notification cancelled successfully');
            loadNotificationHistory();
        } else {
            throw new Error(data.detail || 'Failed to cancel notification');
        }
    } catch (error) {
        console.error('Error cancelling notification:', error);
        showError('Failed to cancel notification');
    }
}

/**
 * Perform bulk operation
 */
function performBulkOperation() {
    const operation = document.getElementById('bulkOperation').value;
    
    if (!operation) {
        showError('Please select a bulk operation');
        return;
    }
    
    if (selectedNotifications.size === 0) {
        showError('Please select notifications to perform bulk operation');
        return;
    }
    
    showBulkOperationModal(operation);
}

/**
 * Show bulk operation modal
 */
function showBulkOperationModal(operation) {
    const modal = document.getElementById('bulkModal');
    const formContainer = document.getElementById('bulkOperationForm');
    
    let formHTML = `<p><strong>Operation:</strong> ${operation}</p>`;
    formHTML += `<p><strong>Selected Notifications:</strong> ${selectedNotifications.size}</p>`;
    
    if (operation === 'cancel') {
        formHTML += `
            <div class="filter-group">
                <label for="cancelReason">Reason for cancellation (optional):</label>
                <input type="text" id="cancelReason" placeholder="Enter reason...">
            </div>
        `;
    }
    
    formContainer.innerHTML = formHTML;
    modal.style.display = 'block';
}

/**
 * Confirm bulk operation
 */
async function confirmBulkOperation() {
    const operation = document.getElementById('bulkOperation').value;
    const notificationIds = Array.from(selectedNotifications);
    
    try {
        const body = {
            operation: operation,
            notification_ids: notificationIds
        };
        
        if (operation === 'cancel') {
            const reason = document.getElementById('cancelReason').value;
            if (reason) {
                body.reason = reason;
            }
        }
        
        const response = await fetch(`${API_BASE}/bulk-operations`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(body)
        });
        
        const data = await response.json();
        
        if (data.success) {
            showSuccess(`Bulk operation completed: ${data.data.successful} successful, ${data.data.failed} failed`);
            selectedNotifications.clear();
            closeBulkModal();
            loadNotificationHistory();
        } else {
            throw new Error(data.detail || 'Bulk operation failed');
        }
    } catch (error) {
        console.error('Error performing bulk operation:', error);
        showError('Bulk operation failed');
    }
}

/**
 * Export data
 */
async function exportData() {
    const format = prompt('Enter export format (csv, json, excel):', 'csv');
    
    if (!format || !['csv', 'json', 'excel'].includes(format.toLowerCase())) {
        showError('Invalid export format');
        return;
    }
    
    try {
        const params = new URLSearchParams({
            format: format.toLowerCase(),
            ...currentFilters
        });
        
        const response = await fetch(`${API_BASE}/export?${params}`);
        
        if (response.ok) {
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `notification_history_${new Date().toISOString().split('T')[0]}.${format}`;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
        } else {
            throw new Error('Export failed');
        }
    } catch (error) {
        console.error('Error exporting data:', error);
        showError('Export failed');
    }
}

/**
 * Show analytics
 */
async function showAnalytics() {
    try {
        const response = await fetch(`${API_BASE}/analytics`);
        const data = await response.json();
        
        if (data.success) {
            displayAnalytics(data.data);
            document.getElementById('analyticsSection').style.display = 'block';
        } else {
            throw new Error('Failed to load analytics');
        }
    } catch (error) {
        console.error('Error loading analytics:', error);
        showError('Failed to load analytics');
    }
}

/**
 * Hide analytics
 */
function hideAnalytics() {
    document.getElementById('analyticsSection').style.display = 'none';
}

/**
 * Display analytics charts
 */
function displayAnalytics(analytics) {
    // Status distribution chart
    const statusCtx = document.getElementById('statusChart').getContext('2d');
    if (charts.statusChart) {
        charts.statusChart.destroy();
    }
    
    charts.statusChart = new Chart(statusCtx, {
        type: 'doughnut',
        data: {
            labels: analytics.status_distribution.map(item => item.status),
            datasets: [{
                data: analytics.status_distribution.map(item => item.count),
                backgroundColor: [
                    '#28a745', '#ffc107', '#dc3545', '#6c757d',
                    '#17a2b8', '#fd7e14', '#6f42c1', '#e83e8c'
                ]
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false
        }
    });
    
    // Channel distribution chart
    const channelCtx = document.getElementById('channelChart').getContext('2d');
    if (charts.channelChart) {
        charts.channelChart.destroy();
    }
    
    charts.channelChart = new Chart(channelCtx, {
        type: 'bar',
        data: {
            labels: analytics.channel_distribution.map(item => item.channel),
            datasets: [{
                label: 'Count',
                data: analytics.channel_distribution.map(item => item.count),
                backgroundColor: '#667eea'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false
        }
    });
    
    // Time trends chart
    const trendCtx = document.getElementById('trendChart').getContext('2d');
    if (charts.trendChart) {
        charts.trendChart.destroy();
    }
    
    charts.trendChart = new Chart(trendCtx, {
        type: 'line',
        data: {
            labels: analytics.time_trends.map(item => item.time_period),
            datasets: [{
                label: 'Notifications',
                data: analytics.time_trends.map(item => item.count),
                borderColor: '#667eea',
                backgroundColor: 'rgba(102, 126, 234, 0.1)',
                fill: true
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false
        }
    });
    
    // Top recipients chart
    const recipientsCtx = document.getElementById('recipientsChart').getContext('2d');
    if (charts.recipientsChart) {
        charts.recipientsChart.destroy();
    }
    
    charts.recipientsChart = new Chart(recipientsCtx, {
        type: 'horizontalBar',
        data: {
            labels: analytics.top_recipients.map(item => item.recipient.substring(0, 20) + '...'),
            datasets: [{
                label: 'Count',
                data: analytics.top_recipients.map(item => item.count),
                backgroundColor: '#28a745'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false
        }
    });
}

/**
 * Initialize charts
 */
function initializeCharts() {
    // Initialize empty charts
    const chartIds = ['statusChart', 'channelChart', 'trendChart', 'recipientsChart'];
    
    chartIds.forEach(id => {
        const canvas = document.getElementById(id);
        if (canvas) {
            const ctx = canvas.getContext('2d');
            charts[id] = new Chart(ctx, {
                type: 'doughnut',
                data: { labels: [], datasets: [] },
                options: { responsive: true, maintainAspectRatio: false }
            });
        }
    });
}

/**
 * Refresh data
 */
function refreshData() {
    loadSummaryStats();
    loadNotificationHistory();
}

/**
 * Close modal
 */
function closeModal() {
    document.getElementById('notificationModal').style.display = 'none';
}

/**
 * Close bulk modal
 */
function closeBulkModal() {
    document.getElementById('bulkModal').style.display = 'none';
    document.getElementById('bulkOperation').value = '';
}

/**
 * Show loading state
 */
function showLoading() {
    const tbody = document.getElementById('notificationsTableBody');
    tbody.innerHTML = '<tr><td colspan="9" class="loading">Loading...</td></tr>';
}

/**
 * Show error message
 */
function showError(message) {
    const errorDiv = document.createElement('div');
    errorDiv.className = 'error';
    errorDiv.textContent = message;
    
    const container = document.querySelector('.notification-management');
    container.insertBefore(errorDiv, container.firstChild);
    
    setTimeout(() => {
        errorDiv.remove();
    }, 5000);
}

/**
 * Show success message
 */
function showSuccess(message) {
    const successDiv = document.createElement('div');
    successDiv.className = 'success';
    successDiv.textContent = message;
    
    const container = document.querySelector('.notification-management');
    container.insertBefore(successDiv, container.firstChild);
    
    setTimeout(() => {
        successDiv.remove();
    }, 5000);
}

/**
 * Format date time
 */
function formatDateTime(dateTimeString) {
    if (!dateTimeString) return 'N/A';
    
    const date = new Date(dateTimeString);
    return date.toLocaleString();
}

// Close modals when clicking outside
window.onclick = function(event) {
    const notificationModal = document.getElementById('notificationModal');
    const bulkModal = document.getElementById('bulkModal');
    
    if (event.target === notificationModal) {
        closeModal();
    }
    if (event.target === bulkModal) {
        closeBulkModal();
    }
} 