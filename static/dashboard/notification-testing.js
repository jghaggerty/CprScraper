/**
 * Notification Testing Tools JavaScript
 *
 * This file provides the frontend functionality for the notification testing interface,
 * including test execution, result display, and system status monitoring.
 */

// Global variables
let selectedTestType = null;
let currentTestResults = [];
let isTestRunning = false;

// API base URL
const API_BASE = '/api/notification-testing';

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
    console.log('Initializing notification testing interface...');
    
    // Load test types
    await loadTestTypes();
    
    // Load system status
    await loadSystemStatus();
    
    // Load configuration validation
    await loadConfigurationValidation();
}

/**
 * Load initial data
 */
async function loadInitialData() {
    try {
        // Load test types
        await loadTestTypes();
        
        // Load system status
        await loadSystemStatus();
        
        console.log('Initial data loaded successfully');
    } catch (error) {
        console.error('Failed to load initial data:', error);
        showError('Failed to load initial data. Please refresh the page.');
    }
}

/**
 * Set up event listeners
 */
function setupEventListeners() {
    // Test type selection
    document.getElementById('runSelectedTest').addEventListener('click', runSelectedTest);
    document.getElementById('runComprehensiveTest').addEventListener('click', runComprehensiveTest);
    
    // Configuration and status
    document.getElementById('validateConfiguration').addEventListener('click', validateConfiguration);
    document.getElementById('refreshStatus').addEventListener('click', refreshStatus);
    
    // Report actions
    document.getElementById('downloadReport').addEventListener('click', downloadReport);
    document.getElementById('clearResults').addEventListener('click', clearResults);
}

/**
 * Load available test types from the API
 */
async function loadTestTypes() {
    try {
        const response = await fetch(`${API_BASE}/test-types`, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${getAuthToken()}`
            }
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        
        if (data.success) {
            populateTestTypes(data.test_types);
        } else {
            throw new Error(data.message || 'Failed to load test types');
        }
        
    } catch (error) {
        console.error('Failed to load test types:', error);
        showError('Failed to load test types: ' + error.message);
    }
}

/**
 * Populate test types in the UI
 */
function populateTestTypes(testTypes) {
    const testTypesGrid = document.getElementById('testTypesGrid');
    testTypesGrid.innerHTML = '';
    
    testTypes.forEach(testType => {
        const testTypeItem = document.createElement('div');
        testTypeItem.className = 'test-type-item';
        testTypeItem.dataset.testType = testType.value;
        
        testTypeItem.innerHTML = `
            <h4>${testType.name}</h4>
            <p>${testType.description}</p>
            <span class="category">${testType.category}</span>
        `;
        
        testTypeItem.addEventListener('click', () => selectTestType(testType.value));
        testTypesGrid.appendChild(testTypeItem);
    });
}

/**
 * Select a test type
 */
function selectTestType(testType) {
    // Remove previous selection
    document.querySelectorAll('.test-type-item').forEach(item => {
        item.classList.remove('selected');
    });
    
    // Add selection to clicked item
    const selectedItem = document.querySelector(`[data-test-type="${testType}"]`);
    if (selectedItem) {
        selectedItem.classList.add('selected');
    }
    
    selectedTestType = testType;
    document.getElementById('runSelectedTest').disabled = false;
}

/**
 * Run the selected individual test
 */
async function runSelectedTest() {
    if (!selectedTestType) {
        showError('Please select a test type first.');
        return;
    }
    
    if (isTestRunning) {
        showError('A test is already running. Please wait for it to complete.');
        return;
    }
    
    try {
        isTestRunning = true;
        updateSystemStatus('running');
        showProgress();
        
        const response = await fetch(`${API_BASE}/run-individual-test`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${getAuthToken()}`
            },
            body: JSON.stringify({
                test_type: selectedTestType,
                test_config: {}
            })
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        
        if (data.success) {
            // Add result to current results
            currentTestResults.push(data.result);
            
            // Display results
            displayTestResults([data.result]);
            
            // Generate and display report
            await generateTestReport();
            
            showSuccess(`Test '${data.result.test_name}' completed successfully`);
        } else {
            throw new Error(data.message || 'Test failed');
        }
        
    } catch (error) {
        console.error('Test failed:', error);
        showError('Test failed: ' + error.message);
        
        // Add failed result
        const failedResult = {
            test_type: selectedTestType,
            test_name: `Test: ${selectedTestType}`,
            success: false,
            duration: 0,
            details: {},
            error_message: error.message,
            timestamp: new Date().toISOString()
        };
        
        currentTestResults.push(failedResult);
        displayTestResults([failedResult]);
        
    } finally {
        isTestRunning = false;
        updateSystemStatus('ready');
        hideProgress();
    }
}

/**
 * Run comprehensive test suite
 */
async function runComprehensiveTest() {
    if (isTestRunning) {
        showError('A test is already running. Please wait for it to complete.');
        return;
    }
    
    try {
        isTestRunning = true;
        updateSystemStatus('running');
        showProgress();
        
        const response = await fetch(`${API_BASE}/run-comprehensive-test`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${getAuthToken()}`
            }
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        
        if (data.success) {
            // Update current results
            currentTestResults = data.results.test_results.map(result => ({
                test_type: result.test_type,
                test_name: result.test_name,
                success: result.success,
                duration: result.duration,
                details: result.details,
                error_message: result.error_message,
                timestamp: result.timestamp
            }));
            
            // Display results
            displayTestResults(currentTestResults);
            
            // Generate and display report
            await generateTestReport();
            
            showSuccess(`Comprehensive test suite completed: ${data.results.summary.passed_tests}/${data.results.summary.total_tests} tests passed`);
        } else {
            throw new Error(data.message || 'Comprehensive test failed');
        }
        
    } catch (error) {
        console.error('Comprehensive test failed:', error);
        showError('Comprehensive test failed: ' + error.message);
        
    } finally {
        isTestRunning = false;
        updateSystemStatus('ready');
        hideProgress();
    }
}

/**
 * Load system status
 */
async function loadSystemStatus() {
    try {
        const response = await fetch(`${API_BASE}/test-status`, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${getAuthToken()}`
            }
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        
        if (data.success) {
            updateSystemStatus(data.status);
            updateConfigurationPanel(data);
        } else {
            throw new Error(data.message || 'Failed to load system status');
        }
        
    } catch (error) {
        console.error('Failed to load system status:', error);
        updateSystemStatus('error');
    }
}

/**
 * Update system status display
 */
function updateSystemStatus(status) {
    const systemStatus = document.getElementById('systemStatus');
    
    // Remove existing status classes
    systemStatus.innerHTML = '';
    
    let statusClass = 'status-ready';
    let statusText = 'Ready';
    let statusIcon = 'fas fa-circle';
    
    switch (status) {
        case 'ready':
            statusClass = 'status-ready';
            statusText = 'Ready';
            statusIcon = 'fas fa-circle';
            break;
        case 'running':
            statusClass = 'status-running';
            statusText = 'Running Tests';
            statusIcon = 'fas fa-spinner fa-spin';
            break;
        case 'error':
            statusClass = 'status-error';
            statusText = 'Error';
            statusIcon = 'fas fa-exclamation-triangle';
            break;
        case 'success':
            statusClass = 'status-success';
            statusText = 'Success';
            statusIcon = 'fas fa-check-circle';
            break;
    }
    
    systemStatus.innerHTML = `
        <div class="status-indicator ${statusClass}">
            <i class="${statusIcon}"></i> ${statusText}
        </div>
    `;
}

/**
 * Update configuration panel
 */
function updateConfigurationPanel(data) {
    const configPanel = document.getElementById('configurationPanel');
    
    let configHtml = '';
    
    // Health indicators
    if (data.health_indicators) {
        configHtml += '<h4>System Health</h4>';
        Object.entries(data.health_indicators).forEach(([key, value]) => {
            const statusClass = value ? 'config-valid' : 'config-invalid';
            const statusText = value ? 'OK' : 'Error';
            configHtml += `
                <div class="config-item">
                    <span class="config-label">${key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}</span>
                    <span class="config-status ${statusClass}">${statusText}</span>
                </div>
            `;
        });
    }
    
    // Channel status
    if (data.channel_status) {
        configHtml += '<h4>Notification Channels</h4>';
        Object.entries(data.channel_status).forEach(([channel, status]) => {
            const statusClass = status.configured ? 'config-valid' : 'config-warning';
            const statusText = status.configured ? 'Configured' : 'Not Configured';
            configHtml += `
                <div class="config-item">
                    <span class="config-label">${channel.charAt(0).toUpperCase() + channel.slice(1)}</span>
                    <span class="config-status ${statusClass}">${statusText}</span>
                </div>
            `;
        });
    }
    
    configPanel.innerHTML = configHtml;
}

/**
 * Validate configuration
 */
async function validateConfiguration() {
    try {
        const response = await fetch(`${API_BASE}/validate-configuration`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${getAuthToken()}`
            }
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        
        if (data.success) {
            const validation = data.validation;
            
            if (validation.configuration_valid) {
                showSuccess('Configuration validation passed');
            } else {
                showError('Configuration validation failed: ' + validation.errors.join(', '));
            }
            
            // Update configuration panel with validation results
            updateConfigurationValidation(validation);
            
        } else {
            throw new Error(data.message || 'Configuration validation failed');
        }
        
    } catch (error) {
        console.error('Configuration validation failed:', error);
        showError('Configuration validation failed: ' + error.message);
    }
}

/**
 * Load configuration validation
 */
async function loadConfigurationValidation() {
    try {
        const response = await fetch(`${API_BASE}/validate-configuration`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${getAuthToken()}`
            }
        });
        
        if (response.ok) {
            const data = await response.json();
            if (data.success) {
                updateConfigurationValidation(data.validation);
            }
        }
    } catch (error) {
        console.error('Failed to load configuration validation:', error);
    }
}

/**
 * Update configuration validation display
 */
function updateConfigurationValidation(validation) {
    const configPanel = document.getElementById('configurationPanel');
    
    let validationHtml = '<h4>Configuration Validation</h4>';
    
    // Errors
    if (validation.errors && validation.errors.length > 0) {
        validation.errors.forEach(error => {
            validationHtml += `
                <div class="config-item">
                    <span class="config-label">Error</span>
                    <span class="config-status config-invalid">${error}</span>
                </div>
            `;
        });
    }
    
    // Warnings
    if (validation.warnings && validation.warnings.length > 0) {
        validation.warnings.forEach(warning => {
            validationHtml += `
                <div class="config-item">
                    <span class="config-label">Warning</span>
                    <span class="config-status config-warning">${warning}</span>
                </div>
            `;
        });
    }
    
    // Details
    if (validation.details) {
        Object.entries(validation.details).forEach(([key, value]) => {
            validationHtml += `
                <div class="config-item">
                    <span class="config-label">${key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}</span>
                    <span class="config-value">${value}</span>
                </div>
            `;
        });
    }
    
    // Add validation section to existing content
    configPanel.innerHTML += validationHtml;
}

/**
 * Refresh system status
 */
async function refreshStatus() {
    await loadSystemStatus();
    await loadConfigurationValidation();
    showSuccess('System status refreshed');
}

/**
 * Display test results
 */
function displayTestResults(results) {
    const testResults = document.getElementById('testResults');
    const testResultsContent = document.getElementById('testResultsContent');
    
    testResultsContent.innerHTML = '';
    
    results.forEach(result => {
        const resultItem = document.createElement('div');
        resultItem.className = `test-result-item ${result.success ? 'success' : 'error'}`;
        
        const statusText = result.success ? 'PASS' : 'FAIL';
        const statusClass = result.success ? 'status-success' : 'status-error';
        
        resultItem.innerHTML = `
            <div class="test-result-header">
                <span class="test-result-name">${result.test_name}</span>
                <span class="status-indicator ${statusClass}">${statusText}</span>
            </div>
            <div class="test-result-details">
                <div class="test-result-duration">Duration: ${result.duration.toFixed(2)}s</div>
                <div>Type: ${result.test_type}</div>
                ${result.error_message ? `<div class="test-result-error">Error: ${result.error_message}</div>` : ''}
            </div>
        `;
        
        testResultsContent.appendChild(resultItem);
    });
    
    testResults.classList.remove('hidden');
}

/**
 * Generate test report
 */
async function generateTestReport() {
    try {
        const response = await fetch(`${API_BASE}/test-report?format=text`, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${getAuthToken()}`
            },
            body: JSON.stringify({
                test_results: currentTestResults
            })
        });
        
        if (response.ok) {
            const data = await response.json();
            if (data.success) {
                displayTestReport(data.report);
            }
        }
    } catch (error) {
        console.error('Failed to generate test report:', error);
    }
}

/**
 * Display test report
 */
function displayTestReport(report) {
    const reportSection = document.getElementById('reportSection');
    const reportContent = document.getElementById('reportContent');
    
    reportContent.textContent = report;
    reportSection.classList.remove('hidden');
}

/**
 * Download test report
 */
function downloadReport() {
    const reportContent = document.getElementById('reportContent').textContent;
    const blob = new Blob([reportContent], { type: 'text/plain' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `notification-test-report-${new Date().toISOString().split('T')[0]}.txt`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    window.URL.revokeObjectURL(url);
}

/**
 * Clear test results
 */
function clearResults() {
    currentTestResults = [];
    document.getElementById('testResults').classList.add('hidden');
    document.getElementById('reportSection').classList.add('hidden');
    document.getElementById('testResultsContent').innerHTML = '';
    document.getElementById('reportContent').textContent = '';
    
    // Clear test type selection
    document.querySelectorAll('.test-type-item').forEach(item => {
        item.classList.remove('selected');
    });
    selectedTestType = null;
    document.getElementById('runSelectedTest').disabled = true;
    
    showSuccess('Test results cleared');
}

/**
 * Show progress indicator
 */
function showProgress() {
    const progressContainer = document.getElementById('progressContainer');
    const progressBar = document.getElementById('progressBar');
    
    progressContainer.classList.remove('hidden');
    progressBar.style.width = '0%';
    
    // Animate progress bar
    let progress = 0;
    const interval = setInterval(() => {
        progress += Math.random() * 15;
        if (progress > 90) progress = 90;
        progressBar.style.width = progress + '%';
        
        if (!isTestRunning) {
            progressBar.style.width = '100%';
            setTimeout(() => {
                progressContainer.classList.add('hidden');
            }, 500);
            clearInterval(interval);
        }
    }, 200);
}

/**
 * Hide progress indicator
 */
function hideProgress() {
    const progressContainer = document.getElementById('progressContainer');
    const progressBar = document.getElementById('progressBar');
    
    progressBar.style.width = '100%';
    setTimeout(() => {
        progressContainer.classList.add('hidden');
    }, 500);
}

/**
 * Get authentication token
 */
function getAuthToken() {
    // This should be implemented based on your authentication system
    // For now, return a placeholder
    return localStorage.getItem('authToken') || '';
}

/**
 * Show success message
 */
function showSuccess(message) {
    // Create a temporary success message
    const successDiv = document.createElement('div');
    successDiv.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        background: #28a745;
        color: white;
        padding: 15px 20px;
        border-radius: 5px;
        z-index: 1000;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    `;
    successDiv.textContent = message;
    
    document.body.appendChild(successDiv);
    
    setTimeout(() => {
        document.body.removeChild(successDiv);
    }, 3000);
}

/**
 * Show error message
 */
function showError(message) {
    // Create a temporary error message
    const errorDiv = document.createElement('div');
    errorDiv.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        background: #dc3545;
        color: white;
        padding: 15px 20px;
        border-radius: 5px;
        z-index: 1000;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    `;
    errorDiv.textContent = message;
    
    document.body.appendChild(errorDiv);
    
    setTimeout(() => {
        document.body.removeChild(errorDiv);
    }, 5000);
} 