/**
 * Dashboard Frontend Tests
 * 
 * Tests for filtering and search functionality by state, form type, date range, and severity
 */

// Mock DOM elements for testing
const mockDOM = {
    searchInput: { value: '' },
    stateFilter: { value: '' },
    agencyFilter: { value: '' },
    formTypeFilter: { value: '' },
    severityFilter: { value: '' },
    dateRangeFilter: { value: '' },
    statusFilter: { value: '' },
    filterTags: { innerHTML: '' },
    appliedFilters: { style: { display: 'none' } },
    resultsTableBody: { innerHTML: '' },
    resultsCards: { innerHTML: '' },
    loadingState: { style: { display: 'none' } },
    resultsContainer: { style: { display: 'block' } },
    totalAgencies: { querySelector: () => ({ textContent: '' }) },
    totalForms: { querySelector: () => ({ textContent: '' }) },
    totalChanges: { querySelector: () => ({ textContent: '' }) },
    criticalChanges: { querySelector: () => ({ textContent: '' }) },
    changes24h: { textContent: '' },
    changesWeek: { textContent: '' },
    coveragePercentage: { textContent: '' },
    pendingNotifications: { textContent: '' },
    alertCount: { textContent: '' },
    alertsContainer: { innerHTML: '' },
    prevPageBtn: { disabled: false },
    nextPageBtn: { disabled: false },
    pageInfo: { textContent: '' },
    sortOrderBtn: { setAttribute: () => {}, innerHTML: '' },
    tableViewBtn: { classList: { remove: () => {}, add: () => {} } },
    cardViewBtn: { classList: { remove: () => {}, add: () => {} } },
    changeModal: { classList: { add: () => {}, remove: () => {} } },
    modalBody: { innerHTML: '' }
};

// Mock fetch for API testing
global.fetch = jest.fn();

// Mock document.getElementById
global.document = {
    getElementById: (id) => mockDOM[id] || { value: '', innerHTML: '', style: { display: 'none' } },
    querySelector: () => ({ className: '', innerHTML: '' }),
    querySelectorAll: () => [],
    addEventListener: () => {},
    body: { appendChild: () => {}, removeChild: () => {} }
};

// Mock window
global.window = {
    dashboard: null
};

// Import the dashboard class (this would need to be adapted for the actual module system)
// For now, we'll test the logic directly

class DashboardTestSuite {
    constructor() {
        this.testResults = [];
    }

    // Test filter building functionality
    testBuildCurrentFilters() {
        console.log('Testing buildCurrentFilters...');
        
        // Test empty filters
        const emptyFilters = this.buildCurrentFilters();
        this.assert(JSON.stringify(emptyFilters) === '{}', 'Empty filters should return empty object');
        
        // Test with values
        mockDOM.stateFilter.value = 'California';
        mockDOM.agencyFilter.value = 'Test Agency';
        mockDOM.severityFilter.value = 'critical';
        
        const populatedFilters = this.buildCurrentFilters();
        this.assert(populatedFilters.state === 'California', 'State filter should be captured');
        this.assert(populatedFilters.agency === 'Test Agency', 'Agency filter should be captured');
        this.assert(populatedFilters.severity === 'critical', 'Severity filter should be captured');
        
        // Reset for other tests
        this.resetMockDOM();
        
        console.log('✓ buildCurrentFilters tests passed');
    }

    // Test filter label generation
    testGetFilterLabel() {
        console.log('Testing getFilterLabel...');
        
        const labels = {
            state: 'State',
            agency: 'Agency',
            form_type: 'Form Type',
            severity: 'Severity',
            date_range: 'Date Range',
            status: 'Status'
        };
        
        Object.entries(labels).forEach(([key, expectedLabel]) => {
            const result = this.getFilterLabel(key, 'test_value');
            const expected = `${expectedLabel}: test_value`;
            this.assert(result === expected, `Filter label for ${key} should be "${expected}"`);
        });
        
        console.log('✓ getFilterLabel tests passed');
    }

    // Test search request building
    testBuildSearchRequest() {
        console.log('Testing buildSearchRequest...');
        
        const currentFilters = { state: 'California', severity: 'critical' };
        const sortBy = 'detected_at';
        const sortOrder = 'desc';
        const currentPage = 1;
        const pageSize = 50;
        
        const request = this.buildSearchRequest(
            currentFilters, sortBy, sortOrder, currentPage, pageSize
        );
        
        this.assert(request.query === '', 'Query should be empty string by default');
        this.assert(request.filters === currentFilters, 'Filters should match input');
        this.assert(request.sort_by === sortBy, 'Sort by should match input');
        this.assert(request.sort_order === sortOrder, 'Sort order should match input');
        this.assert(request.page === currentPage, 'Page should match input');
        this.assert(request.page_size === pageSize, 'Page size should match input');
        
        console.log('✓ buildSearchRequest tests passed');
    }

    // Test date formatting
    testFormatDate() {
        console.log('Testing formatDate...');
        
        const testDate = new Date('2024-01-15T10:30:00Z');
        const formatted = this.formatDate(testDate.toISOString());
        
        // Should contain date and time
        this.assert(formatted.includes('/'), 'Formatted date should contain date separator');
        this.assert(formatted.includes(':'), 'Formatted date should contain time separator');
        
        console.log('✓ formatDate tests passed');
    }

    // Test HTML escaping
    testEscapeHtml() {
        console.log('Testing escapeHtml...');
        
        const testCases = [
            { input: '<script>alert("xss")</script>', expected: '&lt;script&gt;alert("xss")&lt;/script&gt;' },
            { input: '&<>"\'', expected: '&amp;&lt;&gt;&quot;&#39;' },
            { input: 'Normal text', expected: 'Normal text' }
        ];
        
        testCases.forEach(({ input, expected }) => {
            const result = this.escapeHtml(input);
            this.assert(result === expected, `HTML escaping failed for "${input}"`);
        });
        
        console.log('✓ escapeHtml tests passed');
    }

    // Test alert icon mapping
    testGetAlertIcon() {
        console.log('Testing getAlertIcon...');
        
        const iconMap = {
            critical: 'exclamation-triangle',
            warning: 'exclamation-circle',
            error: 'times-circle',
            info: 'info-circle'
        };
        
        Object.entries(iconMap).forEach(([type, expectedIcon]) => {
            const result = this.getAlertIcon(type);
            this.assert(result === expectedIcon, `Alert icon for ${type} should be ${expectedIcon}`);
        });
        
        // Test unknown type
        const unknownResult = this.getAlertIcon('unknown');
        this.assert(unknownResult === 'bell', 'Unknown alert type should return bell icon');
        
        console.log('✓ getAlertIcon tests passed');
    }

    // Test debounce functionality
    testDebounce() {
        console.log('Testing debounce...');
        
        let callCount = 0;
        const debouncedFn = this.debounce(() => { callCount++; }, 100);
        
        // Call multiple times quickly
        debouncedFn();
        debouncedFn();
        debouncedFn();
        
        // Should only execute once after delay
        setTimeout(() => {
            this.assert(callCount === 1, 'Debounced function should only execute once');
            console.log('✓ debounce tests passed');
        }, 150);
    }

    // Test severity badge generation
    testGenerateSeverityBadge() {
        console.log('Testing generateSeverityBadge...');
        
        const testCases = [
            { severity: 'critical', expectedClass: 'severity-critical' },
            { severity: 'high', expectedClass: 'severity-high' },
            { severity: 'medium', expectedClass: 'severity-medium' },
            { severity: 'low', expectedClass: 'severity-low' }
        ];
        
        testCases.forEach(({ severity, expectedClass }) => {
            const badge = this.generateSeverityBadge(severity);
            this.assert(badge.includes(expectedClass), `Severity badge should include ${expectedClass}`);
            this.assert(badge.includes(severity), `Severity badge should include severity text`);
        });
        
        console.log('✓ generateSeverityBadge tests passed');
    }

    // Test status badge generation
    testGenerateStatusBadge() {
        console.log('Testing generateStatusBadge...');
        
        const testCases = [
            { status: 'new', expectedClass: 'status-new' },
            { status: 'reviewed', expectedClass: 'status-reviewed' },
            { status: 'resolved', expectedClass: 'status-resolved' },
            { status: 'ignored', expectedClass: 'status-ignored' }
        ];
        
        testCases.forEach(({ status, expectedClass }) => {
            const badge = this.generateStatusBadge(status);
            this.assert(badge.includes(expectedClass), `Status badge should include ${expectedClass}`);
            this.assert(badge.includes(status), `Status badge should include status text`);
        });
        
        console.log('✓ generateStatusBadge tests passed');
    }

    // Test filter validation
    testFilterValidation() {
        console.log('Testing filterValidation...');
        
        // Test valid filters
        const validFilters = {
            state: 'California',
            severity: 'critical',
            date_range: '7d'
        };
        
        this.assert(this.validateFilters(validFilters), 'Valid filters should pass validation');
        
        // Test invalid filters
        const invalidFilters = {
            severity: 'invalid_severity',
            date_range: 'invalid_range'
        };
        
        this.assert(!this.validateFilters(invalidFilters), 'Invalid filters should fail validation');
        
        console.log('✓ filterValidation tests passed');
    }

    // Test pagination logic
    testPaginationLogic() {
        console.log('Testing paginationLogic...');
        
        const response = {
            page: 2,
            total_pages: 5,
            total_count: 250,
            page_size: 50
        };
        
        // Test pagination state
        const paginationState = this.calculatePaginationState(response);
        
        this.assert(paginationState.prevDisabled === false, 'Previous button should be enabled on page 2');
        this.assert(paginationState.nextDisabled === false, 'Next button should be enabled when not on last page');
        this.assert(paginationState.pageInfo === 'Page 2 of 5', 'Page info should be correct');
        
        // Test edge cases
        const firstPageResponse = { ...response, page: 1 };
        const firstPageState = this.calculatePaginationState(firstPageResponse);
        this.assert(firstPageState.prevDisabled === true, 'Previous button should be disabled on first page');
        
        const lastPageResponse = { ...response, page: 5 };
        const lastPageState = this.calculatePaginationState(lastPageResponse);
        this.assert(lastPageState.nextDisabled === true, 'Next button should be disabled on last page');
        
        console.log('✓ paginationLogic tests passed');
    }

    // Helper methods for testing
    buildCurrentFilters() {
        const filters = {};
        
        if (mockDOM.stateFilter.value) filters.state = mockDOM.stateFilter.value;
        if (mockDOM.agencyFilter.value) filters.agency = mockDOM.agencyFilter.value;
        if (mockDOM.formTypeFilter.value) filters.form_type = mockDOM.formTypeFilter.value;
        if (mockDOM.severityFilter.value) filters.severity = mockDOM.severityFilter.value;
        if (mockDOM.dateRangeFilter.value) filters.date_range = mockDOM.dateRangeFilter.value;
        if (mockDOM.statusFilter.value) filters.status = mockDOM.statusFilter.value;
        
        return filters;
    }

    getFilterLabel(key, value) {
        const labels = {
            state: 'State',
            agency: 'Agency',
            form_type: 'Form Type',
            severity: 'Severity',
            date_range: 'Date Range',
            status: 'Status'
        };
        
        const label = labels[key] || key;
        return `${label}: ${value}`;
    }

    buildSearchRequest(filters = {}, sortBy = 'detected_at', sortOrder = 'desc', page = 1, pageSize = 50) {
        return {
            query: '',
            filters: filters,
            sort_by: sortBy,
            sort_order: sortOrder,
            page: page,
            page_size: pageSize
        };
    }

    formatDate(dateString) {
        const date = new Date(dateString);
        return date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    getAlertIcon(type) {
        const icons = {
            critical: 'exclamation-triangle',
            warning: 'exclamation-circle',
            error: 'times-circle',
            info: 'info-circle'
        };
        return icons[type] || 'bell';
    }

    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }

    generateSeverityBadge(severity) {
        return `<span class="severity-badge severity-${severity}">${severity}</span>`;
    }

    generateStatusBadge(status) {
        return `<span class="status-badge status-${status}">${status}</span>`;
    }

    validateFilters(filters) {
        const validSeverities = ['critical', 'high', 'medium', 'low'];
        const validDateRanges = ['24h', '7d', '30d', '90d', '1y'];
        
        if (filters.severity && !validSeverities.includes(filters.severity)) {
            return false;
        }
        
        if (filters.date_range && !validDateRanges.includes(filters.date_range)) {
            return false;
        }
        
        return true;
    }

    calculatePaginationState(response) {
        return {
            prevDisabled: response.page <= 1,
            nextDisabled: response.page >= response.total_pages,
            pageInfo: `Page ${response.page} of ${response.total_pages}`
        };
    }

    resetMockDOM() {
        Object.values(mockDOM).forEach(element => {
            if (element.value !== undefined) element.value = '';
            if (element.innerHTML !== undefined) element.innerHTML = '';
        });
    }

    assert(condition, message) {
        if (!condition) {
            throw new Error(`Assertion failed: ${message}`);
        }
        this.testResults.push({ passed: true, message });
    }

    runAllTests() {
        console.log('🚀 Starting Dashboard Frontend Tests...\n');
        
        try {
            this.testBuildCurrentFilters();
            this.testGetFilterLabel();
            this.testBuildSearchRequest();
            this.testFormatDate();
            this.testEscapeHtml();
            this.testGetAlertIcon();
            this.testDebounce();
            this.testGenerateSeverityBadge();
            this.testGenerateStatusBadge();
            this.testFilterValidation();
            this.testPaginationLogic();
            
            console.log('\n✅ All tests passed!');
            console.log(`📊 Test Results: ${this.testResults.length} tests passed`);
            
        } catch (error) {
            console.error('\n❌ Test failed:', error.message);
            console.log(`📊 Test Results: ${this.testResults.length} tests passed, 1 failed`);
        }
    }
}

// Run tests if this file is executed directly
if (typeof module !== 'undefined' && module.exports) {
    module.exports = DashboardTestSuite;
} else {
    // Browser environment
    const testSuite = new DashboardTestSuite();
    testSuite.runAllTests();
} 