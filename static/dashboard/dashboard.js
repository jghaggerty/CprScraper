/**
 * Compliance Monitoring Dashboard JavaScript
 * 
 * Implements filtering and search functionality by state, form type, date range, and severity
 * Provides real-time data updates and interactive dashboard features
 */

class ComplianceDashboard {
    constructor() {
        this.apiBase = '/api/dashboard';
        this.realtimeApiBase = '/api/realtime';
        this.authApiBase = '/api/auth';
        this.currentFilters = {};
        this.currentPage = 1;
        this.pageSize = 50;
        this.sortBy = 'detected_at';
        this.sortOrder = 'desc';
        this.currentView = 'table';
        this.filterOptions = {};
        this.isLoading = false;
        
        // Authentication and user management
        this.currentUser = null;
        this.userPermissions = [];
        this.userRoles = [];
        
        // Real-time features
        this.websocket = null;
        this.realtimeEnabled = true;
        this.lastUpdateTime = null;
        this.monitoringStatus = {};
        this.liveStatistics = {};
        this.systemHealth = {};
        this.activeAlerts = [];
        
        // Analytics and Chart Management
        this.trendChart = null;
        this.agencyChart = null;
        
        this.init();
    }

    async init() {
        try {
            // Check authentication first
            if (!await this.checkAuthentication()) {
                window.location.href = '/auth/login.html';
                return;
            }
            
            // Initialize event listeners
            this.setupEventListeners();
            
            // Load initial data
            await this.loadFilterOptions();
            await this.loadDashboardStats();
            await this.loadRecentChanges();
            await this.loadAlerts();
            
            // Initialize real-time features
            await this.initializeRealtimeFeatures();
            
            // Initialize analytics
            await this.initializeAnalytics();
            
                    // Initialize widgets
        await this.initializeWidgets();
        
        // Initialize export features
        await this.initializeExportFeatures();
            
            // Initialize mobile menu
            this.initializeMobileMenu();
            
            // Set up auto-refresh
            this.setupAutoRefresh();
            
        } catch (error) {
            console.error('Dashboard initialization failed:', error);
            this.showError('Failed to initialize dashboard');
        }
    }

    setupEventListeners() {
        // Filter controls
        document.getElementById('searchInput').addEventListener('input', this.debounce(() => this.handleSearch(), 300));
        document.getElementById('searchBtn').addEventListener('click', () => this.handleSearch());
        document.getElementById('stateFilter').addEventListener('change', () => this.handleFilterChange());
        document.getElementById('agencyFilter').addEventListener('change', () => this.handleFilterChange());
        document.getElementById('formTypeFilter').addEventListener('change', () => this.handleFilterChange());
        document.getElementById('severityFilter').addEventListener('change', () => this.handleFilterChange());
        document.getElementById('dateRangeFilter').addEventListener('change', () => this.handleFilterChange());
        document.getElementById('statusFilter').addEventListener('change', () => this.handleFilterChange());
        
        // Clear filters
        document.getElementById('clearFiltersBtn').addEventListener('click', () => this.clearAllFilters());
        
        // Sort controls
        document.getElementById('sortBy').addEventListener('change', () => this.handleSortChange());
        document.getElementById('sortOrderBtn').addEventListener('click', () => this.toggleSortOrder());
        
        // View controls
        document.getElementById('tableViewBtn').addEventListener('click', () => this.switchView('table'));
        document.getElementById('cardViewBtn').addEventListener('click', () => this.switchView('cards'));
        
        // Pagination
        document.getElementById('prevPageBtn').addEventListener('click', () => this.previousPage());
        document.getElementById('nextPageBtn').addEventListener('click', () => this.nextPage());
        
        // Refresh button
        document.getElementById('refreshBtn').addEventListener('click', () => this.refreshData());
        
        // Logout button
        document.getElementById('logoutBtn').addEventListener('click', () => this.logout());
        
        // Modal controls
        document.getElementById('closeModalBtn').addEventListener('click', () => this.closeModal());
        document.getElementById('closeSidebarBtn').addEventListener('click', () => this.closeSidebar());
        
        // Close modal when clicking outside
        document.getElementById('changeModal').addEventListener('click', (e) => {
            if (e.target.id === 'changeModal') {
                this.closeModal();
            }
        });

        // Widget event listeners
        this.setupWidgetEventListeners();
    }

    setupWidgetEventListeners() {
        // Widget refresh buttons
        document.getElementById('refreshWidgetsBtn').addEventListener('click', () => this.refreshAllWidgets());
        document.getElementById('refreshRecentChangesBtn').addEventListener('click', () => this.loadRecentChangesWidget());
        document.getElementById('refreshAlertsBtn').addEventListener('click', () => this.loadPendingAlertsWidget());
        document.getElementById('refreshComplianceBtn').addEventListener('click', () => this.loadComplianceStatusWidget());
        document.getElementById('refreshAgencyHealthBtn').addEventListener('click', () => this.loadAgencyHealthWidget());
        document.getElementById('refreshActivityBtn').addEventListener('click', () => this.loadMonitoringActivityWidget());

        // Widget action buttons
        document.getElementById('viewAllChangesBtn').addEventListener('click', () => this.scrollToSection('results-section'));
        document.getElementById('viewAllAlertsBtn').addEventListener('click', () => this.scrollToSection('alerts-section'));
        document.getElementById('viewComplianceReportBtn').addEventListener('click', () => this.generateComplianceReport());
        document.getElementById('viewAgencyDetailsBtn').addEventListener('click', () => this.showAgencyDetails());
        document.getElementById('viewMonitoringLogBtn').addEventListener('click', () => this.showMonitoringLog());

        // Quick action buttons
        document.getElementById('exportDataBtn').addEventListener('click', () => this.handleQuickAction('export'));
        document.getElementById('generateReportBtn').addEventListener('click', () => this.handleQuickAction('report'));
        document.getElementById('scheduleMonitoringBtn').addEventListener('click', () => this.handleQuickAction('schedule'));
        document.getElementById('manageNotificationsBtn').addEventListener('click', () => this.handleQuickAction('notifications'));
        document.getElementById('viewAnalyticsBtn').addEventListener('click', () => this.handleQuickAction('analytics'));
        document.getElementById('systemHealthBtn').addEventListener('click', () => this.handleQuickAction('health'));

        // Widget view toggle
        document.getElementById('widgetGridBtn').addEventListener('click', () => this.switchWidgetView('grid'));
        document.getElementById('widgetListBtn').addEventListener('click', () => this.switchWidgetView('list'));
    }

    // Authentication Methods
    async checkAuthentication() {
        const token = localStorage.getItem('authToken');
        if (!token) {
            return false;
        }

        try {
            const response = await fetch(`${this.authApiBase}/me`, {
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json',
                }
            });

            if (response.ok) {
                const userData = await response.json();
                this.currentUser = {
                    id: userData.user_id,
                    username: userData.username,
                    email: userData.email,
                    firstName: userData.first_name,
                    lastName: userData.last_name
                };
                this.userRoles = userData.roles;
                this.userPermissions = userData.permissions;
                this.updateUserInterface();
                return true;
            } else {
                localStorage.removeItem('authToken');
                localStorage.removeItem('userData');
                return false;
            }
        } catch (error) {
            console.error('Authentication check failed:', error);
            return false;
        }
    }

    updateUserInterface() {
        // Update user info in header
        const userInfoElement = document.getElementById('userInfo');
        if (userInfoElement && this.currentUser) {
            userInfoElement.innerHTML = `
                <span class="user-name">${this.currentUser.firstName} ${this.currentUser.lastName}</span>
                <span class="user-role">${this.userRoles.join(', ')}</span>
            `;
        }

        // Show/hide features based on permissions
        this.updatePermissionBasedUI();
    }

    updatePermissionBasedUI() {
        // User management features
        const userManagementElements = document.querySelectorAll('[data-permission="users:read"], [data-permission="users:write"]');
        userManagementElements.forEach(element => {
            const requiredPermission = element.dataset.permission;
            if (!this.userPermissions.includes(requiredPermission)) {
                element.style.display = 'none';
            }
        });

        // Role management features
        const roleManagementElements = document.querySelectorAll('[data-permission="roles:read"], [data-permission="roles:write"]');
        roleManagementElements.forEach(element => {
            const requiredPermission = element.dataset.permission;
            if (!this.userPermissions.includes(requiredPermission)) {
                element.style.display = 'none';
            }
        });

        // Export features
        const exportElements = document.querySelectorAll('[data-permission="export:read"], [data-permission="export:write"]');
        exportElements.forEach(element => {
            const requiredPermission = element.dataset.permission;
            if (!this.userPermissions.includes(requiredPermission)) {
                element.style.display = 'none';
            }
        });
    }

    logout() {
        localStorage.removeItem('authToken');
        localStorage.removeItem('userData');
        window.location.href = '/auth/login.html';
    }

    // API Methods
    async apiRequest(endpoint, options = {}) {
        const url = `${this.apiBase}${endpoint}`;
        const config = {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
            },
            ...options
        };

        // Add authentication header if available
        const token = localStorage.getItem('authToken');
        if (token) {
            config.headers['Authorization'] = `Bearer ${token}`;
        }

        try {
            const response = await fetch(url, config);
            
            if (response.status === 401) {
                // Token expired or invalid, redirect to login
                this.logout();
                return;
            }
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return await response.json();
        } catch (error) {
            console.error(`API request failed for ${endpoint}:`, error);
            throw error;
        }
    }

    async loadFilterOptions() {
        try {
            this.filterOptions = await this.apiRequest('/filters');
            this.populateFilterOptions();
        } catch (error) {
            console.error('Failed to load filter options:', error);
        }
    }

    async loadDashboardStats() {
        try {
            const stats = await this.apiRequest('/stats');
            this.updateDashboardStats(stats);
            this.updateSystemHealth(stats.system_health);
        } catch (error) {
            console.error('Failed to load dashboard stats:', error);
        }
    }

    async loadRecentChanges() {
        if (this.isLoading) return;
        
        this.setLoading(true);
        try {
            const searchRequest = this.buildSearchRequest();
            const response = await this.apiRequest('/search', {
                method: 'POST',
                body: JSON.stringify(searchRequest)
            });
            
            this.displayResults(response);
            this.updatePagination(response);
        } catch (error) {
            console.error('Failed to load recent changes:', error);
            this.showError('Failed to load recent changes');
        } finally {
            this.setLoading(false);
        }
    }

    async loadAlerts() {
        try {
            const alerts = await this.apiRequest('/alerts');
            this.displayAlerts(alerts);
        } catch (error) {
            console.error('Failed to load alerts:', error);
        }
    }

    // Filter Methods
    handleSearch() {
        const searchQuery = document.getElementById('searchInput').value.trim();
        if (searchQuery !== this.currentFilters.query) {
            this.currentFilters.query = searchQuery;
            this.currentPage = 1;
            this.loadRecentChanges();
        }
    }

    handleFilterChange() {
        const newFilters = this.buildCurrentFilters();
        if (JSON.stringify(newFilters) !== JSON.stringify(this.currentFilters)) {
            this.currentFilters = newFilters;
            this.currentPage = 1;
            this.updateAppliedFilters();
            this.loadRecentChanges();
        }
    }

    buildCurrentFilters() {
        const filters = {};
        
        const stateFilter = document.getElementById('stateFilter').value;
        if (stateFilter) filters.state = stateFilter;
        
        const agencyFilter = document.getElementById('agencyFilter').value;
        if (agencyFilter) filters.agency = agencyFilter;
        
        const formTypeFilter = document.getElementById('formTypeFilter').value;
        if (formTypeFilter) filters.form_type = formTypeFilter;
        
        const severityFilter = document.getElementById('severityFilter').value;
        if (severityFilter) filters.severity = severityFilter;
        
        const dateRangeFilter = document.getElementById('dateRangeFilter').value;
        if (dateRangeFilter) filters.date_range = dateRangeFilter;
        
        const statusFilter = document.getElementById('statusFilter').value;
        if (statusFilter) filters.status = statusFilter;
        
        return filters;
    }

    clearAllFilters() {
        // Clear all filter inputs
        document.getElementById('searchInput').value = '';
        document.getElementById('stateFilter').value = '';
        document.getElementById('agencyFilter').value = '';
        document.getElementById('formTypeFilter').value = '';
        document.getElementById('severityFilter').value = '';
        document.getElementById('dateRangeFilter').value = '';
        document.getElementById('statusFilter').value = '';
        
        // Reset current filters
        this.currentFilters = {};
        this.currentPage = 1;
        
        // Update UI and reload data
        this.updateAppliedFilters();
        this.loadRecentChanges();
    }

    updateAppliedFilters() {
        const filterTagsContainer = document.getElementById('filterTags');
        filterTagsContainer.innerHTML = '';
        
        const appliedFilters = [];
        
        // Add search query
        if (this.currentFilters.query) {
            appliedFilters.push({
                key: 'query',
                label: `Search: "${this.currentFilters.query}"`,
                value: this.currentFilters.query
            });
        }
        
        // Add other filters
        Object.entries(this.currentFilters).forEach(([key, value]) => {
            if (key !== 'query') {
                const label = this.getFilterLabel(key, value);
                appliedFilters.push({ key, label, value });
            }
        });
        
        // Display filter tags
        appliedFilters.forEach(filter => {
            const tag = document.createElement('div');
            tag.className = 'filter-tag';
            tag.innerHTML = `
                ${filter.label}
                <button class="remove-tag" onclick="dashboard.removeFilter('${filter.key}')">
                    <i class="fas fa-times"></i>
                </button>
            `;
            filterTagsContainer.appendChild(tag);
        });
        
        // Show/hide applied filters section
        const appliedFiltersSection = document.getElementById('appliedFilters');
        appliedFiltersSection.style.display = appliedFilters.length > 0 ? 'block' : 'none';
    }

    removeFilter(key) {
        if (key === 'query') {
            document.getElementById('searchInput').value = '';
        } else {
            const filterElement = document.getElementById(`${key}Filter`);
            if (filterElement) {
                filterElement.value = '';
            }
        }
        
        delete this.currentFilters[key];
        this.currentPage = 1;
        this.updateAppliedFilters();
        this.loadRecentChanges();
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

    // Sort Methods
    handleSortChange() {
        this.sortBy = document.getElementById('sortBy').value;
        this.loadRecentChanges();
    }

    toggleSortOrder() {
        this.sortOrder = this.sortOrder === 'desc' ? 'asc' : 'desc';
        const sortOrderBtn = document.getElementById('sortOrderBtn');
        sortOrderBtn.setAttribute('data-order', this.sortOrder);
        sortOrderBtn.innerHTML = this.sortOrder === 'desc' 
            ? '<i class="fas fa-sort-amount-down"></i>'
            : '<i class="fas fa-sort-amount-up"></i>';
        this.loadRecentChanges();
    }

    // View Methods
    switchView(view) {
        this.currentView = view;
        
        // Update view buttons
        document.querySelectorAll('.view-btn').forEach(btn => {
            btn.classList.remove('active');
        });
        document.getElementById(`${view}ViewBtn`).classList.add('active');
        
        // Show/hide view containers
        document.getElementById('resultsContainer').style.display = view === 'table' ? 'block' : 'none';
        document.getElementById('resultsCards').style.display = view === 'cards' ? 'grid' : 'none';
        
        // Reload data to update view
        this.loadRecentChanges();
    }

    // Pagination Methods
    previousPage() {
        if (this.currentPage > 1) {
            this.currentPage--;
            this.loadRecentChanges();
        }
    }

    nextPage() {
        this.currentPage++;
        this.loadRecentChanges();
    }

    // Display Methods
    updateDashboardStats(stats) {
        document.getElementById('totalAgencies').querySelector('.stat-number').textContent = stats.total_agencies;
        document.getElementById('totalForms').querySelector('.stat-number').textContent = stats.active_forms;
        document.getElementById('totalChanges').querySelector('.stat-number').textContent = stats.total_changes;
        document.getElementById('criticalChanges').querySelector('.stat-number').textContent = stats.critical_changes;
        
        // Update sidebar stats
        document.getElementById('changes24h').textContent = stats.changes_last_24h;
        document.getElementById('changesWeek').textContent = stats.changes_last_week;
        document.getElementById('coveragePercentage').textContent = `${stats.coverage_percentage}%`;
        document.getElementById('pendingNotifications').textContent = stats.pending_notifications;
    }

    updateSystemHealth(health) {
        const healthIndicator = document.querySelector('.health-indicator');
        healthIndicator.className = `health-indicator ${health}`;
        
        const healthText = health === 'healthy' ? 'System Healthy' : 
                          health === 'degraded' ? 'System Degraded' : 'System Critical';
        
        healthIndicator.innerHTML = `<i class="fas fa-circle"></i> ${healthText}`;
    }

    displayResults(response) {
        if (this.currentView === 'table') {
            this.displayTableResults(response.results);
        } else {
            this.displayCardResults(response.results);
        }
    }

    displayTableResults(results) {
        const tbody = document.getElementById('resultsTableBody');
        tbody.innerHTML = '';
        
        if (results.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="8" style="text-align: center; padding: 2rem; color: #6b7280;">
                        No changes found matching your criteria
                    </td>
                </tr>
            `;
            return;
        }
        
        results.forEach(change => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>
                    <div>
                        <div style="font-weight: 500;">${this.escapeHtml(change.form_name)}</div>
                        <div style="font-size: 0.75rem; color: #6b7280;">${this.escapeHtml(change.agency_type)}</div>
                    </div>
                </td>
                <td>${this.escapeHtml(change.agency_name)}</td>
                <td>${this.escapeHtml(change.change_type)}</td>
                <td>
                    <span class="severity-badge severity-${change.severity}">
                        ${change.severity}
                    </span>
                </td>
                <td>
                    <span class="status-badge status-${change.status}">
                        ${change.status}
                    </span>
                </td>
                <td>${this.formatDate(change.detected_at)}</td>
                <td>
                    ${change.ai_confidence_score ? 
                        `<div class="ai-confidence">
                            <div style="font-weight: 500;">${change.ai_confidence_score}%</div>
                            <div style="font-size: 0.75rem; color: #6b7280;">${change.ai_change_category || 'N/A'}</div>
                        </div>` : 
                        'N/A'
                    }
                </td>
                <td>
                    <button class="btn btn-secondary" onclick="dashboard.showChangeDetails(${change.id})">
                        <i class="fas fa-eye"></i> View
                    </button>
                </td>
            `;
            tbody.appendChild(row);
        });
    }

    displayCardResults(results) {
        const cardsContainer = document.getElementById('resultsCards');
        cardsContainer.innerHTML = '';
        
        if (results.length === 0) {
            cardsContainer.innerHTML = `
                <div style="grid-column: 1 / -1; text-align: center; padding: 2rem; color: #6b7280;">
                    No changes found matching your criteria
                </div>
            `;
            return;
        }
        
        results.forEach(change => {
            const card = document.createElement('div');
            card.className = 'change-card';
            card.innerHTML = `
                <div class="card-header">
                    <div>
                        <div class="card-title">${this.escapeHtml(change.form_name)}</div>
                        <div class="card-subtitle">${this.escapeHtml(change.agency_name)}</div>
                    </div>
                    <span class="severity-badge severity-${change.severity}">
                        ${change.severity}
                    </span>
                </div>
                <div class="card-content">
                    <div class="card-row">
                        <span class="card-label">Change Type:</span>
                        <span class="card-value">${this.escapeHtml(change.change_type)}</span>
                    </div>
                    <div class="card-row">
                        <span class="card-label">Status:</span>
                        <span class="status-badge status-${change.status}">${change.status}</span>
                    </div>
                    <div class="card-row">
                        <span class="card-label">Detected:</span>
                        <span class="card-value">${this.formatDate(change.detected_at)}</span>
                    </div>
                    ${change.ai_confidence_score ? `
                        <div class="card-row">
                            <span class="card-label">AI Confidence:</span>
                            <span class="card-value">${change.ai_confidence_score}%</span>
                        </div>
                    ` : ''}
                    <div class="card-row" style="margin-top: 0.5rem;">
                        <button class="btn btn-secondary" onclick="dashboard.showChangeDetails(${change.id})">
                            <i class="fas fa-eye"></i> View Details
                        </button>
                    </div>
                </div>
            `;
            cardsContainer.appendChild(card);
        });
    }

    displayAlerts(alerts) {
        const alertsContainer = document.getElementById('alertsContainer');
        const alertCount = document.getElementById('alertCount');
        
        alertCount.textContent = alerts.total_alerts;
        
        if (alerts.alerts.length === 0) {
            alertsContainer.innerHTML = `
                <div style="text-align: center; padding: 1rem; color: #6b7280;">
                    No active alerts
                </div>
            `;
            return;
        }
        
        alertsContainer.innerHTML = '';
        alerts.alerts.forEach(alert => {
            const alertElement = document.createElement('div');
            alertElement.className = `alert-item alert-${alert.type}`;
            alertElement.innerHTML = `
                <i class="fas fa-${this.getAlertIcon(alert.type)}"></i>
                <div>
                    <div style="font-weight: 500;">${alert.message}</div>
                    <div style="font-size: 0.875rem; opacity: 0.8;">Count: ${alert.count}</div>
                </div>
            `;
            alertsContainer.appendChild(alertElement);
        });
    }

    updatePagination(response) {
        const prevBtn = document.getElementById('prevPageBtn');
        const nextBtn = document.getElementById('nextPageBtn');
        const pageInfo = document.getElementById('pageInfo');
        
        prevBtn.disabled = response.page <= 1;
        nextBtn.disabled = response.page >= response.total_pages;
        
        pageInfo.textContent = `Page ${response.page} of ${response.total_pages}`;
    }

    populateFilterOptions() {
        // Populate state filter
        const stateFilter = document.getElementById('stateFilter');
        this.filterOptions.states.forEach(state => {
            const option = document.createElement('option');
            option.value = state;
            option.textContent = state;
            stateFilter.appendChild(option);
        });
        
        // Populate agency filter
        const agencyFilter = document.getElementById('agencyFilter');
        this.filterOptions.agencies.forEach(agency => {
            const option = document.createElement('option');
            option.value = agency;
            option.textContent = agency;
            agencyFilter.appendChild(option);
        });
        
        // Populate form type filter
        const formTypeFilter = document.getElementById('formTypeFilter');
        this.filterOptions.form_types.forEach(formType => {
            const option = document.createElement('option');
            option.value = formType;
            option.textContent = formType;
            formTypeFilter.appendChild(option);
        });
    }

    // Utility Methods
    buildSearchRequest() {
        return {
            query: this.currentFilters.query || '',
            filters: this.currentFilters,
            sort_by: this.sortBy,
            sort_order: this.sortOrder,
            page: this.currentPage,
            page_size: this.pageSize
        };
    }

    setLoading(loading) {
        this.isLoading = loading;
        const loadingState = document.getElementById('loadingState');
        const resultsContainer = document.getElementById('resultsContainer');
        const resultsCards = document.getElementById('resultsCards');
        
        if (loading) {
            loadingState.style.display = 'flex';
            resultsContainer.style.display = 'none';
            resultsCards.style.display = 'none';
        } else {
            loadingState.style.display = 'none';
            if (this.currentView === 'table') {
                resultsContainer.style.display = 'block';
            } else {
                resultsCards.style.display = 'grid';
            }
        }
    }

    showChangeDetails(changeId) {
        // This would typically fetch detailed change information
        // For now, we'll show a placeholder modal
        const modal = document.getElementById('changeModal');
        const modalBody = document.getElementById('modalBody');
        
        modalBody.innerHTML = `
            <div style="text-align: center; padding: 2rem;">
                <i class="fas fa-info-circle" style="font-size: 3rem; color: #3b82f6; margin-bottom: 1rem;"></i>
                <h4>Change Details</h4>
                <p>Detailed information for change ID: ${changeId}</p>
                <p style="color: #6b7280; font-size: 0.875rem;">
                    This would show comprehensive change details including before/after comparisons, 
                    impact assessment, and related metadata.
                </p>
            </div>
        `;
        
        modal.classList.add('show');
    }

    closeModal() {
        document.getElementById('changeModal').classList.remove('show');
    }

    closeSidebar() {
        const sidebar = document.getElementById('sidebar');
        const sidebarOverlay = document.getElementById('sidebarOverlay');
        
        sidebar.classList.remove('show');
        if (sidebarOverlay) {
            sidebarOverlay.classList.remove('show');
        }
        document.body.style.overflow = '';
    }

    refreshData() {
        this.loadDashboardStats();
        this.loadRecentChanges();
        this.loadAlerts();
    }

    setupAutoRefresh() {
        // Auto-refresh every 5 minutes
        setInterval(() => {
            this.refreshData();
        }, 5 * 60 * 1000);
    }

    showError(message) {
        // Create a simple error notification
        const errorDiv = document.createElement('div');
        errorDiv.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: #ef4444;
            color: white;
            padding: 1rem;
            border-radius: 8px;
            z-index: 10000;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
        `;
        errorDiv.textContent = message;
        document.body.appendChild(errorDiv);
        
        setTimeout(() => {
            errorDiv.remove();
        }, 5000);
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

    initializeMobileMenu() {
        const mobileMenuBtn = document.getElementById('mobileMenuBtn');
        const sidebar = document.getElementById('sidebar');
        const sidebarOverlay = document.getElementById('sidebarOverlay');
        
        if (mobileMenuBtn) {
            mobileMenuBtn.addEventListener('click', () => {
                sidebar.classList.add('show');
                sidebarOverlay.classList.add('show');
                document.body.style.overflow = 'hidden';
            });
        }
        
        if (sidebarOverlay) {
            sidebarOverlay.addEventListener('click', () => {
                sidebar.classList.remove('show');
                sidebarOverlay.classList.remove('show');
                document.body.style.overflow = '';
            });
        }
        
        // Close sidebar on escape key
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && sidebar.classList.contains('show')) {
                sidebar.classList.remove('show');
                sidebarOverlay.classList.remove('show');
                document.body.style.overflow = '';
            }
        });
    }

    // Real-time monitoring methods
    async initializeRealtimeFeatures() {
        try {
            // Initialize WebSocket connection
            await this.initializeWebSocket();
            
            // Load initial real-time data
            await this.loadMonitoringStatus();
            await this.loadLiveStatistics();
            await this.loadSystemHealth();
            
            // Set up real-time update intervals
            this.setupRealtimeUpdates();
            
        } catch (error) {
            console.error('Failed to initialize real-time features:', error);
            this.realtimeEnabled = false;
        }
    }

    // Analytics and Chart Management
    async initializeAnalytics() {
        try {
            // Initialize charts
            this.initializeCharts();
            
            // Load initial analytics data
            await this.loadTrendsSummary();
            await this.loadAgencyPerformance();
            await this.loadHistoricalData();
            
            // Set up analytics event listeners
            this.setupAnalyticsEventListeners();
            
        } catch (error) {
            console.error('Failed to initialize analytics:', error);
        }
    }

    initializeCharts() {
        // Initialize trend chart
        const trendCtx = document.getElementById('trendChart');
        if (trendCtx) {
            this.trendChart = new Chart(trendCtx, {
                type: 'line',
                data: {
                    labels: [],
                    datasets: [{
                        label: 'Changes',
                        data: [],
                        borderColor: '#3b82f6',
                        backgroundColor: 'rgba(59, 130, 246, 0.1)',
                        borderWidth: 2,
                        fill: true,
                        tension: 0.4
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            display: false
                        }
                    },
                    scales: {
                        y: {
                            beginAtZero: true,
                            grid: {
                                color: 'rgba(0, 0, 0, 0.1)'
                            }
                        },
                        x: {
                            grid: {
                                display: false
                            }
                        }
                    }
                }
            });
        }

        // Initialize agency performance chart
        const agencyCtx = document.getElementById('agencyPerformanceChart');
        if (agencyCtx) {
            this.agencyChart = new Chart(agencyCtx, {
                type: 'bar',
                data: {
                    labels: [],
                    datasets: [{
                        label: 'Performance Score',
                        data: [],
                        backgroundColor: '#10b981',
                        borderColor: '#059669',
                        borderWidth: 1
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            display: false
                        }
                    },
                    scales: {
                        y: {
                            beginAtZero: true,
                            max: 100,
                            grid: {
                                color: 'rgba(0, 0, 0, 0.1)'
                            }
                        },
                        x: {
                            grid: {
                                display: false
                            }
                        }
                    }
                }
            });
        }
    }

    setupAnalyticsEventListeners() {
        // Chart metric change
        const chartMetric = document.getElementById('chartMetric');
        if (chartMetric) {
            chartMetric.addEventListener('change', () => {
                this.loadHistoricalData();
            });
        }

        // Chart period change
        const chartPeriod = document.getElementById('chartPeriod');
        if (chartPeriod) {
            chartPeriod.addEventListener('change', () => {
                this.loadHistoricalData();
            });
        }

        // Refresh charts button
        const refreshChartsBtn = document.getElementById('refreshChartsBtn');
        if (refreshChartsBtn) {
            refreshChartsBtn.addEventListener('click', () => {
                this.refreshAnalytics();
            });
        }
    }

    async loadTrendsSummary() {
        try {
            const response = await this.apiRequest('/trends/summary');
            this.updateTrendsSummary(response);
        } catch (error) {
            console.error('Failed to load trends summary:', error);
        }
    }

    async loadAgencyPerformance() {
        try {
            const response = await this.apiRequest('/analytics/agency-performance');
            this.updateAgencyPerformanceChart(response);
        } catch (error) {
            console.error('Failed to load agency performance:', error);
        }
    }

    async loadHistoricalData() {
        try {
            const metric = document.getElementById('chartMetric')?.value || 'changes';
            const period = document.getElementById('chartPeriod')?.value || '30d';
            
            const request = {
                metric: metric,
                period: period,
                group_by: 'day',
                filters: this.getCurrentFilters()
            };

            const response = await fetch(`${this.apiBase}/historical-data`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(request)
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            this.updateTrendChart(data);
        } catch (error) {
            console.error('Failed to load historical data:', error);
        }
    }

    async refreshAnalytics() {
        try {
            await Promise.all([
                this.loadTrendsSummary(),
                this.loadAgencyPerformance(),
                this.loadHistoricalData()
            ]);
        } catch (error) {
            console.error('Failed to refresh analytics:', error);
        }
    }

    updateTrendsSummary(data) {
        // Update changes trend
        const changesTrendDesc = document.getElementById('changesTrendDesc');
        const changesTrendPercent = document.getElementById('changesTrendPercent');
        if (changesTrendDesc && changesTrendPercent && data.changes_trend) {
            changesTrendDesc.textContent = data.changes_trend.description;
            changesTrendPercent.textContent = `${data.changes_trend.percentage > 0 ? '+' : ''}${data.changes_trend.percentage.toFixed(1)}%`;
            changesTrendPercent.className = `trend-percentage ${data.changes_trend.percentage > 5 ? 'positive' : data.changes_trend.percentage < -5 ? 'negative' : 'neutral'}`;
        }

        // Update critical changes trend
        const criticalTrendDesc = document.getElementById('criticalTrendDesc');
        const criticalTrendPercent = document.getElementById('criticalTrendPercent');
        if (criticalTrendDesc && criticalTrendPercent && data.critical_trend) {
            criticalTrendDesc.textContent = data.critical_trend.description;
            criticalTrendPercent.textContent = `${data.critical_trend.percentage > 0 ? '+' : ''}${data.critical_trend.percentage.toFixed(1)}%`;
            criticalTrendPercent.className = `trend-percentage ${data.critical_trend.percentage > 5 ? 'positive' : data.critical_trend.percentage < -5 ? 'negative' : 'neutral'}`;
        }

        // Update response time trend
        const responseTrendDesc = document.getElementById('responseTrendDesc');
        const responseTrendPercent = document.getElementById('responseTrendPercent');
        if (responseTrendDesc && responseTrendPercent && data.response_time_trend) {
            responseTrendDesc.textContent = data.response_time_trend.description;
            responseTrendPercent.textContent = `${data.response_time_trend.percentage > 0 ? '+' : ''}${data.response_time_trend.percentage.toFixed(1)}%`;
            responseTrendPercent.className = `trend-percentage ${data.response_time_trend.percentage < -5 ? 'positive' : data.response_time_trend.percentage > 5 ? 'negative' : 'neutral'}`;
        }
    }

    updateAgencyPerformanceChart(data) {
        if (!this.agencyChart || !data.agency_performance) return;

        const labels = data.agency_performance.map(agency => agency.agency_name);
        const scores = data.agency_performance.map(agency => agency.performance_score);

        this.agencyChart.data.labels = labels;
        this.agencyChart.data.datasets[0].data = scores;
        this.agencyChart.update();

        // Update summary
        const avgSuccessRate = document.getElementById('avgSuccessRate');
        if (avgSuccessRate && data.summary) {
            avgSuccessRate.textContent = `${data.summary.avg_success_rate.toFixed(1)}%`;
        }
    }

    updateTrendChart(data) {
        if (!this.trendChart || !data.data_points) return;

        const labels = data.data_points.map(point => point.label);
        const values = data.data_points.map(point => point.value);

        this.trendChart.data.labels = labels;
        this.trendChart.data.datasets[0].data = values;
        this.trendChart.data.datasets[0].label = this.getMetricLabel();
        this.trendChart.update();

        // Update trend indicator
        const trendValue = document.getElementById('trendValue');
        if (trendValue) {
            trendValue.textContent = data.trend_direction;
            trendValue.className = `trend-value ${data.trend_direction}`;
        }
    }

    getMetricLabel() {
        const metric = document.getElementById('chartMetric')?.value || 'changes';
        const labels = {
            'changes': 'Total Changes',
            'critical_changes': 'Critical Changes',
            'monitoring_runs': 'Monitoring Runs',
            'response_times': 'Response Time (ms)'
        };
        return labels[metric] || 'Changes';
    }

    getCurrentFilters() {
        const filters = {};
        
        const agencyId = document.getElementById('agencyFilter')?.value;
        if (agencyId) filters.agency_id = parseInt(agencyId);
        
        const severity = document.getElementById('severityFilter')?.value;
        if (severity) filters.severity = severity;
        
        const status = document.getElementById('statusFilter')?.value;
        if (status) filters.status = status;
        
        return filters;
    }

    async initializeWebSocket() {
        try {
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            const wsUrl = `${protocol}//${window.location.host}${this.realtimeApiBase}/ws`;
            
            this.websocket = new WebSocket(wsUrl);
            
            this.websocket.onopen = () => {
                console.log('WebSocket connected');
                this.updateConnectionStatus(true);
            };
            
            this.websocket.onmessage = (event) => {
                this.handleWebSocketMessage(JSON.parse(event.data));
            };
            
            this.websocket.onclose = () => {
                console.log('WebSocket disconnected');
                this.updateConnectionStatus(false);
                // Attempt to reconnect after 5 seconds
                setTimeout(() => this.initializeWebSocket(), 5000);
            };
            
            this.websocket.onerror = (error) => {
                console.error('WebSocket error:', error);
                this.updateConnectionStatus(false);
            };
            
        } catch (error) {
            console.error('Failed to initialize WebSocket:', error);
            this.realtimeEnabled = false;
        }
    }

    handleWebSocketMessage(message) {
        const { type, timestamp, data } = message;
        
        switch (type) {
            case 'initial_data':
                this.handleInitialData(data);
                break;
            case 'statistics_update':
                this.handleStatisticsUpdate(data);
                break;
            case 'monitoring_status':
                this.handleMonitoringStatusUpdate(data);
                break;
            case 'system_health':
                this.handleSystemHealthUpdate(data);
                break;
            case 'change_detected':
                this.handleChangeDetected(data);
                break;
            case 'alert':
                this.handleAlertUpdate(data);
                break;
            case 'pong':
                // Keep connection alive
                break;
            default:
                console.log('Unknown WebSocket message type:', type);
        }
        
        this.lastUpdateTime = timestamp;
        this.updateLastUpdateTime();
    }

    handleInitialData(data) {
        if (data.statistics) {
            this.updateDashboardStats(data.statistics);
        }
        if (data.monitoring_status) {
            this.updateMonitoringStatus(data.monitoring_status);
        }
        if (data.system_health) {
            this.updateSystemHealth(data.system_health);
        }
    }

    handleStatisticsUpdate(data) {
        this.updateDashboardStats(data);
    }

    handleMonitoringStatusUpdate(data) {
        this.updateMonitoringStatus(data);
    }

    handleSystemHealthUpdate(data) {
        this.updateSystemHealth(data);
    }

    handleChangeDetected(data) {
        // Add new change to the top of the list
        this.addNewChange(data);
        
        // Show notification
        this.showChangeNotification(data);
    }

    handleAlertUpdate(data) {
        this.updateAlerts([data]);
    }

    async loadMonitoringStatus() {
        try {
            const response = await this.apiRequest('/monitoring-status');
            this.updateMonitoringStatus(response);
        } catch (error) {
            console.error('Failed to load monitoring status:', error);
        }
    }

    async loadLiveStatistics() {
        try {
            const response = await this.apiRequest('/live-statistics');
            this.updateLiveStatistics(response);
        } catch (error) {
            console.error('Failed to load live statistics:', error);
        }
    }

    async loadSystemHealth() {
        try {
            const response = await this.apiRequest('/health');
            this.updateSystemHealth(response);
        } catch (error) {
            console.error('Failed to load system health:', error);
        }
    }

    setupRealtimeUpdates() {
        // Send periodic pings to keep WebSocket alive
        setInterval(() => {
            if (this.websocket && this.websocket.readyState === WebSocket.OPEN) {
                this.websocket.send(JSON.stringify({ type: 'ping' }));
            }
        }, 30000);
        
        // Request periodic updates
        setInterval(() => {
            if (this.websocket && this.websocket.readyState === WebSocket.OPEN) {
                this.websocket.send(JSON.stringify({ 
                    type: 'request_update', 
                    request_type: 'monitoring_status' 
                }));
            }
        }, 60000);
    }

    updateConnectionStatus(connected) {
        const statusElement = document.getElementById('connectionStatus');
        if (statusElement) {
            statusElement.textContent = connected ? 'Connected' : 'Disconnected';
            statusElement.className = connected ? 'status-connected' : 'status-disconnected';
        }
    }

    updateLastUpdateTime() {
        const timeElement = document.getElementById('lastUpdateTime');
        if (timeElement && this.lastUpdateTime) {
            const date = new Date(this.lastUpdateTime);
            timeElement.textContent = date.toLocaleTimeString();
        }
    }

    updateMonitoringStatus(status) {
        this.monitoringStatus = status;
        
        // Update monitoring status display
        this.updateMonitoringStatusDisplay(status);
        
        // Update active runs count
        this.updateActiveRunsCount(status.active_runs?.length || 0);
        
        // Update success rate
        if (status.summary) {
            this.updateSuccessRate(status.summary.success_rate);
        }
    }

    updateLiveStatistics(stats) {
        this.liveStatistics = stats;
        
        // Update real-time metrics
        if (stats.real_time_metrics) {
            this.updateRealTimeMetrics(stats.real_time_metrics);
        }
        
        // Update trends
        if (stats.trends) {
            this.updateTrends(stats.trends);
        }
    }

    updateMonitoringStatusDisplay(status) {
        const container = document.getElementById('monitoringStatusContainer');
        if (!container) return;
        
        let html = '<div class="monitoring-status-grid">';
        
        // Active runs
        html += '<div class="status-section">';
        html += '<h4>Active Monitoring Runs</h4>';
        if (status.active_runs && status.active_runs.length > 0) {
            status.active_runs.forEach(run => {
                html += `<div class="run-item active">
                    <span class="run-id">#${run.id}</span>
                    <span class="run-status">${run.status}</span>
                    <span class="run-progress">${run.progress || 0}%</span>
                </div>`;
            });
        } else {
            html += '<p class="no-runs">No active runs</p>';
        }
        html += '</div>';
        
        // Recent completed runs
        html += '<div class="status-section">';
        html += '<h4>Recent Completed Runs</h4>';
        if (status.recent_completed && status.recent_completed.length > 0) {
            status.recent_completed.slice(0, 5).forEach(run => {
                const duration = run.processing_time_seconds ? 
                    `${Math.round(run.processing_time_seconds)}s` : 'N/A';
                html += `<div class="run-item completed">
                    <span class="run-id">#${run.id}</span>
                    <span class="run-status">${run.status}</span>
                    <span class="run-duration">${duration}</span>
                    <span class="run-changes">${run.changes_detected || 0} changes</span>
                </div>`;
            });
        } else {
            html += '<p class="no-runs">No recent completed runs</p>';
        }
        html += '</div>';
        
        html += '</div>';
        container.innerHTML = html;
    }

    updateActiveRunsCount(count) {
        const element = document.getElementById('activeRunsCount');
        if (element) {
            element.textContent = count;
            element.className = count > 0 ? 'active-runs-active' : 'active-runs-inactive';
        }
    }

    updateSuccessRate(rate) {
        const element = document.getElementById('successRate');
        if (element) {
            element.textContent = `${Math.round(rate)}%`;
            element.className = rate >= 95 ? 'success-rate-high' : 
                               rate >= 80 ? 'success-rate-medium' : 'success-rate-low';
        }
    }

    updateRealTimeMetrics(metrics) {
        // Update changes in last hour
        const changesHourElement = document.getElementById('changesLastHour');
        if (changesHourElement) {
            changesHourElement.textContent = metrics.changes_last_hour || 0;
        }
        
        // Update changes in last 15 minutes
        const changes15MinElement = document.getElementById('changesLast15Min');
        if (changes15MinElement) {
            changes15MinElement.textContent = metrics.changes_last_15min || 0;
        }
        
        // Update critical changes
        const criticalChangesElement = document.getElementById('criticalChangesHour');
        if (criticalChangesElement) {
            criticalChangesElement.textContent = metrics.critical_changes_hour || 0;
        }
        
        // Update processing time
        const processingTimeElement = document.getElementById('avgProcessingTime');
        if (processingTimeElement) {
            const time = metrics.avg_processing_time_seconds || 0;
            processingTimeElement.textContent = `${Math.round(time)}s`;
        }
    }

    updateTrends(trends) {
        // Update trend indicators
        Object.keys(trends).forEach(trendKey => {
            const element = document.getElementById(`${trendKey}Trend`);
            if (element) {
                const trend = trends[trendKey];
                element.textContent = trend;
                element.className = `trend-${trend}`;
            }
        });
    }

    addNewChange(change) {
        // Add to the beginning of the results table
        const tbody = document.getElementById('resultsTableBody');
        if (tbody) {
            const newRow = this.createChangeTableRow(change);
            tbody.insertBefore(newRow, tbody.firstChild);
            
            // Remove the last row if we exceed the limit
            if (tbody.children.length > this.pageSize) {
                tbody.removeChild(tbody.lastChild);
            }
        }
        
        // Also update the cards view if active
        const cardsContainer = document.getElementById('resultsCards');
        if (cardsContainer && this.currentView === 'cards') {
            const newCard = this.createChangeCard(change);
            cardsContainer.insertBefore(newCard, cardsContainer.firstChild);
            
            // Remove the last card if we exceed the limit
            if (cardsContainer.children.length > this.pageSize) {
                cardsContainer.removeChild(cardsContainer.lastChild);
            }
        }
    }

    showChangeNotification(change) {
        // Create notification element
        const notification = document.createElement('div');
        notification.className = 'change-notification';
        notification.innerHTML = `
            <div class="notification-content">
                <h4>New Change Detected</h4>
                <p><strong>${change.form_name}</strong> - ${change.agency_name}</p>
                <p>Type: ${change.change_type} | Severity: ${change.severity}</p>
            </div>
            <button class="notification-close" onclick="this.parentElement.remove()">×</button>
        `;
        
        // Add to notification container
        const container = document.getElementById('notificationContainer');
        if (container) {
            container.appendChild(notification);
            
            // Auto-remove after 10 seconds
            setTimeout(() => {
                if (notification.parentElement) {
                    notification.remove();
                }
            }, 10000);
        }
    }

    createChangeTableRow(change) {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${this.escapeHtml(change.form_name || 'Unknown')}</td>
            <td>${this.escapeHtml(change.agency_name || 'Unknown')}</td>
            <td>${this.escapeHtml(change.change_type || 'Unknown')}</td>
            <td><span class="severity-badge ${change.severity}">${change.severity}</span></td>
            <td><span class="status-badge ${change.status}">${change.status}</span></td>
            <td>${this.formatDate(change.detected_at)}</td>
            <td>${change.ai_confidence_score ? `${change.ai_confidence_score}%` : 'N/A'}</td>
            <td>
                <button class="btn btn-sm btn-primary" onclick="dashboard.showChangeDetails(${change.id})">
                    <i class="fas fa-eye"></i> View
                </button>
            </td>
        `;
        return row;
    }

    createChangeCard(change) {
        const card = document.createElement('div');
        card.className = 'change-card';
        card.innerHTML = `
            <div class="card-header">
                <h4>${this.escapeHtml(change.form_name || 'Unknown')}</h4>
                <span class="severity-badge ${change.severity}">${change.severity}</span>
            </div>
            <div class="card-body">
                <p><strong>Agency:</strong> ${this.escapeHtml(change.agency_name || 'Unknown')}</p>
                <p><strong>Type:</strong> ${this.escapeHtml(change.change_type || 'Unknown')}</p>
                <p><strong>Status:</strong> <span class="status-badge ${change.status}">${change.status}</span></p>
                <p><strong>Detected:</strong> ${this.formatDate(change.detected_at)}</p>
                <p><strong>AI Confidence:</strong> ${change.ai_confidence_score ? `${change.ai_confidence_score}%` : 'N/A'}</p>
            </div>
            <div class="card-actions">
                <button class="btn btn-sm btn-primary" onclick="dashboard.showChangeDetails(${change.id})">
                    <i class="fas fa-eye"></i> View Details
                </button>
            </div>
        `;
        return card;
    }

    async initializeWidgets() {
        try {
            // Load all widget data
            await Promise.all([
                this.loadRecentChangesWidget(),
                this.loadPendingAlertsWidget(),
                this.loadComplianceStatusWidget(),
                this.loadAgencyHealthWidget(),
                this.loadMonitoringActivityWidget()
            ]);

            // Set up widget auto-refresh
            this.setupWidgetAutoRefresh();
        } catch (error) {
            console.error('Failed to initialize widgets:', error);
        }
    }

    async loadRecentChangesWidget() {
        try {
            const changes = await this.apiRequest('/changes?limit=5');
            this.updateRecentChangesWidget(changes);
        } catch (error) {
            console.error('Failed to load recent changes widget:', error);
            this.showWidgetError('recentChangesWidget', 'Failed to load recent changes');
        }
    }

    async loadPendingAlertsWidget() {
        try {
            const alerts = await this.apiRequest('/alerts');
            this.updatePendingAlertsWidget(alerts);
        } catch (error) {
            console.error('Failed to load pending alerts widget:', error);
            this.showWidgetError('pendingAlertsWidget', 'Failed to load alerts');
        }
    }

    async loadComplianceStatusWidget() {
        try {
            const stats = await this.apiRequest('/stats');
            this.updateComplianceStatusWidget(stats);
        } catch (error) {
            console.error('Failed to load compliance status widget:', error);
            this.showWidgetError('complianceStatusWidget', 'Failed to load compliance status');
        }
    }

    async loadAgencyHealthWidget() {
        try {
            const agencies = await this.apiRequest('/agencies');
            this.updateAgencyHealthWidget(agencies);
        } catch (error) {
            console.error('Failed to load agency health widget:', error);
            this.showWidgetError('agencyHealthWidget', 'Failed to load agency health');
        }
    }

    async loadMonitoringActivityWidget() {
        try {
            const health = await this.apiRequest('/health');
            this.updateMonitoringActivityWidget(health);
        } catch (error) {
            console.error('Failed to load monitoring activity widget:', error);
            this.showWidgetError('monitoringActivityWidget', 'Failed to load monitoring activity');
        }
    }

    updateRecentChangesWidget(changes) {
        const container = document.getElementById('recentChangesList');
        const lastHourEl = document.getElementById('changesLastHourWidget');
        const last24hEl = document.getElementById('changesLast24hWidget');
        const criticalEl = document.getElementById('criticalChangesWidget');

        // Update stats
        const lastHour = changes.filter(c => {
            const changeTime = new Date(c.detected_at);
            const oneHourAgo = new Date(Date.now() - 60 * 60 * 1000);
            return changeTime > oneHourAgo;
        }).length;

        const last24h = changes.filter(c => {
            const changeTime = new Date(c.detected_at);
            const oneDayAgo = new Date(Date.now() - 24 * 60 * 60 * 1000);
            return changeTime > oneDayAgo;
        }).length;

        const critical = changes.filter(c => c.severity === 'critical').length;

        lastHourEl.textContent = lastHour;
        last24hEl.textContent = last24h;
        criticalEl.textContent = critical;

        // Update list
        if (changes.length === 0) {
            container.innerHTML = '<div class="widget-empty">No recent changes</div>';
            return;
        }

        const changesHtml = changes.slice(0, 5).map(change => `
            <div class="widget-item ${change.severity}">
                <div class="widget-item-icon ${change.severity}">
                    <i class="fas fa-${this.getChangeIcon(change.change_type)}"></i>
                </div>
                <div class="widget-item-content">
                    <div class="widget-item-title">${this.escapeHtml(change.form_name)}</div>
                    <div class="widget-item-subtitle">${this.escapeHtml(change.agency_name)}</div>
                </div>
                <div class="widget-item-time">${this.formatRelativeTime(change.detected_at)}</div>
            </div>
        `).join('');

        container.innerHTML = changesHtml;
    }

    updatePendingAlertsWidget(alerts) {
        const container = document.getElementById('pendingAlertsList');
        const criticalEl = document.getElementById('criticalAlertsWidget');
        const highEl = document.getElementById('highAlertsWidget');
        const totalEl = document.getElementById('totalAlertsWidget');

        const critical = alerts.filter(a => a.severity === 'critical').length;
        const high = alerts.filter(a => a.severity === 'high').length;
        const total = alerts.length;

        criticalEl.textContent = critical;
        highEl.textContent = high;
        totalEl.textContent = total;

        if (alerts.length === 0) {
            container.innerHTML = '<div class="widget-empty">No pending alerts</div>';
            return;
        }

        const alertsHtml = alerts.slice(0, 5).map(alert => `
            <div class="widget-item ${alert.severity}">
                <div class="widget-item-icon ${alert.severity}">
                    <i class="fas fa-${this.getAlertIcon(alert.type)}"></i>
                </div>
                <div class="widget-item-content">
                    <div class="widget-item-title">${this.escapeHtml(alert.title)}</div>
                    <div class="widget-item-subtitle">${this.escapeHtml(alert.description)}</div>
                </div>
                <div class="widget-item-time">${this.formatRelativeTime(alert.created_at)}</div>
            </div>
        `).join('');

        container.innerHTML = alertsHtml;
    }

    updateComplianceStatusWidget(stats) {
        const scoreEl = document.getElementById('complianceScore');
        const statusEl = document.getElementById('complianceStatus');
        const formsUpToDateEl = document.getElementById('formsUpToDate');
        const pendingReviewsEl = document.getElementById('pendingReviews');
        const overdueEl = document.getElementById('overdueItems');

        // Calculate compliance score (simplified calculation)
        const totalForms = stats.total_forms;
        const activeForms = stats.active_forms;
        const complianceScore = totalForms > 0 ? Math.round((activeForms / totalForms) * 100) : 100;

        scoreEl.textContent = complianceScore;
        statusEl.textContent = this.getComplianceStatus(complianceScore);

        // Update compliance breakdown
        formsUpToDateEl.textContent = stats.active_forms;
        pendingReviewsEl.textContent = stats.total_changes - stats.critical_changes;
        overdueEl.textContent = stats.critical_changes;

        // Update score circle
        this.updateComplianceScoreCircle(complianceScore);
    }

    updateAgencyHealthWidget(agencies) {
        const container = document.getElementById('agencyHealthList');
        const healthyEl = document.getElementById('healthyAgencies');
        const warningEl = document.getElementById('warningAgencies');
        const criticalEl = document.getElementById('criticalAgencies');

        const healthy = agencies.filter(a => a.health_status === 'healthy').length;
        const warning = agencies.filter(a => a.health_status === 'warning').length;
        const critical = agencies.filter(a => a.health_status === 'critical').length;

        healthyEl.textContent = healthy;
        warningEl.textContent = warning;
        criticalEl.textContent = critical;

        if (agencies.length === 0) {
            container.innerHTML = '<div class="widget-empty">No agencies found</div>';
            return;
        }

        const agenciesHtml = agencies.slice(0, 5).map(agency => `
            <div class="agency-item ${agency.health_status}">
                <div class="agency-status ${agency.health_status}"></div>
                <div class="agency-name">${this.escapeHtml(agency.name)}</div>
                <div class="agency-forms">${agency.active_forms} forms</div>
            </div>
        `).join('');

        container.innerHTML = agenciesHtml;
    }

    updateMonitoringActivityWidget(health) {
        const container = document.getElementById('monitoringActivityTimeline');
        const activeRunsEl = document.getElementById('activeMonitoringRuns');
        const successRateEl = document.getElementById('monitoringSuccessRate');
        const avgTimeEl = document.getElementById('avgMonitoringTime');

        activeRunsEl.textContent = health.active_monitors || 0;
        successRateEl.textContent = `${Math.round((1 - health.error_rate) * 100)}%`;
        avgTimeEl.textContent = `${Math.round(health.avg_response_time)}s`;

        // Create activity timeline (simplified)
        const activities = [
            { type: 'success', title: 'Monitoring Run Completed', details: 'All agencies checked successfully', time: '2 min ago' },
            { type: 'warning', title: 'Slow Response Detected', details: 'Agency X taking longer than usual', time: '5 min ago' },
            { type: 'success', title: 'Critical Change Detected', details: 'Form Y updated in Agency Z', time: '10 min ago' }
        ];

        const activitiesHtml = activities.map(activity => `
            <div class="activity-item ${activity.type}">
                <div class="activity-icon ${activity.type}">
                    <i class="fas fa-${this.getActivityIcon(activity.type)}"></i>
                </div>
                <div class="activity-content">
                    <div class="activity-title">${this.escapeHtml(activity.title)}</div>
                    <div class="activity-details">${this.escapeHtml(activity.details)}</div>
                </div>
                <div class="activity-time">${activity.time}</div>
            </div>
        `).join('');

        container.innerHTML = activitiesHtml;
    }

    updateComplianceScoreCircle(score) {
        const circle = document.getElementById('complianceScoreCircle');
        const degrees = (score / 100) * 360;
        
        // Update the conic gradient
        circle.style.background = `conic-gradient(#667eea 0deg, #667eea ${degrees}deg, #e2e8f0 ${degrees}deg)`;
    }

    getComplianceStatus(score) {
        if (score >= 90) return 'Excellent';
        if (score >= 75) return 'Good';
        if (score >= 60) return 'Fair';
        return 'Needs Attention';
    }

    getChangeIcon(changeType) {
        const icons = {
            'form_update': 'file-alt',
            'field_change': 'edit',
            'requirement_change': 'exclamation-triangle',
            'deadline_change': 'clock',
            'default': 'info-circle'
        };
        return icons[changeType] || icons.default;
    }

    getActivityIcon(type) {
        const icons = {
            'success': 'check-circle',
            'warning': 'exclamation-triangle',
            'error': 'times-circle',
            'default': 'info-circle'
        };
        return icons[type] || icons.default;
    }

    formatRelativeTime(dateString) {
        const date = new Date(dateString);
        const now = new Date();
        const diffMs = now - date;
        const diffMins = Math.floor(diffMs / (1000 * 60));
        const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
        const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

        if (diffMins < 1) return 'Just now';
        if (diffMins < 60) return `${diffMins}m ago`;
        if (diffHours < 24) return `${diffHours}h ago`;
        return `${diffDays}d ago`;
    }

    async refreshAllWidgets() {
        try {
            await Promise.all([
                this.loadRecentChangesWidget(),
                this.loadPendingAlertsWidget(),
                this.loadComplianceStatusWidget(),
                this.loadAgencyHealthWidget(),
                this.loadMonitoringActivityWidget()
            ]);
        } catch (error) {
            console.error('Failed to refresh widgets:', error);
        }
    }

    setupWidgetAutoRefresh() {
        // Refresh widgets every 5 minutes
        setInterval(() => {
            this.refreshAllWidgets();
        }, 5 * 60 * 1000);
    }

    showWidgetError(widgetId, message) {
        const container = document.getElementById(widgetId);
        if (container) {
            const content = container.querySelector('.widget-content');
            if (content) {
                content.innerHTML = `<div class="widget-error">${message}</div>`;
            }
        }
    }

    scrollToSection(sectionId) {
        const section = document.getElementById(sectionId);
        if (section) {
            section.scrollIntoView({ behavior: 'smooth' });
        }
    }

    async generateComplianceReport() {
        try {
            // This would typically open a modal or navigate to a report page
            this.showError('Compliance report generation not yet implemented');
        } catch (error) {
            console.error('Failed to generate compliance report:', error);
        }
    }

    async showAgencyDetails() {
        try {
            // This would typically open a modal with agency details
            this.showError('Agency details view not yet implemented');
        } catch (error) {
            console.error('Failed to show agency details:', error);
        }
    }

    async showMonitoringLog() {
        try {
            // This would typically open a modal with monitoring log
            this.showError('Monitoring log view not yet implemented');
        } catch (error) {
            console.error('Failed to show monitoring log:', error);
        }
    }

    async handleQuickAction(action) {
        try {
            switch (action) {
                case 'export':
                    this.showError('Export functionality not yet implemented');
                    break;
                case 'report':
                    this.showError('Report generation not yet implemented');
                    break;
                case 'schedule':
                    this.showError('Monitoring scheduling not yet implemented');
                    break;
                case 'notifications':
                    this.showError('Notification settings not yet implemented');
                    break;
                case 'analytics':
                    this.scrollToSection('analytics-section');
                    break;
                case 'health':
                    this.scrollToSection('stats-section');
                    break;
                default:
                    console.warn('Unknown quick action:', action);
            }
        } catch (error) {
            console.error('Failed to handle quick action:', error);
        }
    }

    switchWidgetView(view) {
        const gridBtn = document.getElementById('widgetGridBtn');
        const listBtn = document.getElementById('widgetListBtn');
        const grid = document.getElementById('widgetsGrid');

        if (view === 'grid') {
            gridBtn.classList.add('active');
            listBtn.classList.remove('active');
            grid.style.display = 'grid';
        } else {
            listBtn.classList.add('active');
            gridBtn.classList.remove('active');
            grid.style.display = 'block';
        }
    }

    // Export functionality
    async initializeExportFeatures() {
        try {
            // Load export formats
            await this.loadExportFormats();
            
            // Set up export event listeners
            this.setupExportEventListeners();
            
            // Load export history
            await this.loadExportHistory();
            
        } catch (error) {
            console.error('Failed to initialize export features:', error);
        }
    }

    setupExportEventListeners() {
        // Export data button
        const exportDataBtn = document.getElementById('exportDataBtn');
        if (exportDataBtn) {
            exportDataBtn.addEventListener('click', () => this.handleExportData());
        }

        // Schedule export button
        const scheduleExportBtn = document.getElementById('scheduleExportBtn');
        if (scheduleExportBtn) {
            scheduleExportBtn.addEventListener('click', () => this.handleScheduleExport());
        }

        // Bulk export button
        const bulkExportBtn = document.getElementById('bulkExportBtn');
        if (bulkExportBtn) {
            bulkExportBtn.addEventListener('click', () => this.handleBulkExport());
        }

        // Refresh formats button
        const refreshFormatsBtn = document.getElementById('refreshExportFormatsBtn');
        if (refreshFormatsBtn) {
            refreshFormatsBtn.addEventListener('click', () => this.loadExportFormats());
        }

        // View scheduled exports button
        const viewScheduledBtn = document.getElementById('viewScheduledExportsBtn');
        if (viewScheduledBtn) {
            viewScheduledBtn.addEventListener('click', () => this.handleScheduledExports());
        }

        // Format selection
        const exportFormat = document.getElementById('exportFormat');
        if (exportFormat) {
            exportFormat.addEventListener('change', () => this.updateFormatSelection());
        }

        // Column selection
        const columnCheckboxes = document.querySelectorAll('#columnsSelector input[type="checkbox"]');
        columnCheckboxes.forEach(checkbox => {
            checkbox.addEventListener('change', () => this.updateColumnSelection());
        });
    }

    async loadExportFormats() {
        try {
            const response = await this.apiRequest('/export/formats');
            this.updateExportFormats(response);
        } catch (error) {
            console.error('Failed to load export formats:', error);
        }
    }

    updateExportFormats(formats) {
        const formatsGrid = document.getElementById('formatsGrid');
        if (!formatsGrid) return;

        const formatsHtml = formats.supported_formats.map(format => `
            <div class="format-card" data-format="${format.format}">
                <h4>${format.format.toUpperCase()}</h4>
                <p>${format.description}</p>
                <ul class="format-features">
                    ${format.features.map(feature => `<li>${feature}</li>`).join('')}
                </ul>
                <div style="font-size: 0.75rem; color: #64748b; margin-top: 0.5rem;">
                    Max records: ${format.max_records.toLocaleString()}
                </div>
            </div>
        `).join('');

        formatsGrid.innerHTML = formatsHtml;

        // Add click handlers for format selection
        const formatCards = document.querySelectorAll('.format-card');
        formatCards.forEach(card => {
            card.addEventListener('click', () => {
                // Remove selection from all cards
                formatCards.forEach(c => c.classList.remove('selected'));
                // Add selection to clicked card
                card.classList.add('selected');
                
                // Update format dropdown
                const formatSelect = document.getElementById('exportFormat');
                if (formatSelect) {
                    formatSelect.value = card.dataset.format;
                }
            });
        });
    }

    async handleExportData() {
        try {
            this.showExportStatus('Preparing export...');

            // Get export configuration
            const config = this.getExportConfig();
            
            // Validate configuration
            if (!this.validateExportConfig(config)) {
                this.hideExportStatus();
                return;
            }

            // Make export request
            const response = await fetch(`${this.apiBase}/export`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${localStorage.getItem('token')}`
                },
                body: JSON.stringify(config)
            });

            if (!response.ok) {
                throw new Error(`Export failed: ${response.statusText}`);
            }

            const exportResult = await response.json();
            
            // Show success message
            this.showExportStatus(`Export completed! ${exportResult.record_count} records exported.`);
            
            // Add to export history
            this.addToExportHistory(exportResult);
            
            // Auto-hide status after 5 seconds
            setTimeout(() => this.hideExportStatus(), 5000);

        } catch (error) {
            console.error('Export failed:', error);
            this.showExportStatus(`Export failed: ${error.message}`);
            setTimeout(() => this.hideExportStatus(), 5000);
        }
    }

    getExportConfig() {
        const format = document.getElementById('exportFormat')?.value || 'csv';
        const filename = document.getElementById('exportFilename')?.value || '';
        const includeHeaders = document.getElementById('includeHeaders')?.checked || true;
        const useCurrentFilters = document.getElementById('useCurrentFilters')?.checked || true;

        // Get selected columns
        const selectedColumns = [];
        const columnCheckboxes = document.querySelectorAll('#columnsSelector input[type="checkbox"]:checked');
        columnCheckboxes.forEach(checkbox => {
            selectedColumns.push(checkbox.value);
        });

        const config = {
            format: format,
            columns: selectedColumns.length > 0 ? selectedColumns : undefined,
            include_headers: includeHeaders,
            filename: filename || undefined
        };

        // Add filters if using current filters
        if (useCurrentFilters) {
            config.filters = this.buildCurrentFilters();
        }

        return config;
    }

    validateExportConfig(config) {
        if (!config.format) {
            this.showError('Please select an export format');
            return false;
        }

        if (!config.columns || config.columns.length === 0) {
            this.showError('Please select at least one column to export');
            return false;
        }

        return true;
    }

    showExportStatus(message) {
        const statusElement = document.getElementById('exportStatus');
        const messageElement = document.getElementById('exportStatusMessage');
        
        if (statusElement && messageElement) {
            messageElement.textContent = message;
            statusElement.style.display = 'block';
        }
    }

    hideExportStatus() {
        const statusElement = document.getElementById('exportStatus');
        if (statusElement) {
            statusElement.style.display = 'none';
        }
    }

    async handleScheduleExport() {
        try {
            // Get export configuration
            const exportConfig = this.getExportConfig();
            
            if (!this.validateExportConfig(exportConfig)) {
                return;
            }

            // Show scheduling modal (simplified for now)
            const schedule = {
                frequency: 'daily',
                time: '09:00',
                timezone: 'UTC'
            };

            const scheduleRequest = {
                export_config: exportConfig,
                schedule: schedule
            };

            const response = await fetch(`${this.apiBase}/export/schedule`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${localStorage.getItem('token')}`
                },
                body: JSON.stringify(scheduleRequest)
            });

            if (!response.ok) {
                throw new Error(`Failed to schedule export: ${response.statusText}`);
            }

            const result = await response.json();
            this.showError(`Export scheduled successfully! Next run: ${new Date(result.next_run).toLocaleString()}`);

        } catch (error) {
            console.error('Failed to schedule export:', error);
            this.showError(`Failed to schedule export: ${error.message}`);
        }
    }

    async handleBulkExport() {
        try {
            // Redirect to the dedicated bulk export interface
            window.open('./bulk-export.html', '_blank');
        } catch (error) {
            console.error('Bulk export failed:', error);
            this.showError(`Failed to open bulk export interface: ${error.message}`);
        }
    }

    async handleScheduledExports() {
        try {
            // Redirect to the export scheduling interface
            window.open('./export-scheduling.html', '_blank');
        } catch (error) {
            console.error('Export scheduling failed:', error);
            this.showError(`Failed to open export scheduling interface: ${error.message}`);
        }
    }

    async showScheduledExports() {
        try {
            const response = await this.apiRequest('/export/scheduled');
            this.displayScheduledExports(response.scheduled_exports);
        } catch (error) {
            console.error('Failed to load scheduled exports:', error);
            this.showError('Failed to load scheduled exports');
        }
    }

    displayScheduledExports(exports) {
        // Create a simple modal to show scheduled exports
        const modal = document.getElementById('changeModal');
        const modalBody = document.getElementById('modalBody');
        
        if (exports.length === 0) {
            modalBody.innerHTML = `
                <div style="text-align: center; padding: 2rem;">
                    <i class="fas fa-calendar-alt" style="font-size: 3rem; color: #3b82f6; margin-bottom: 1rem;"></i>
                    <h4>No Scheduled Exports</h4>
                    <p>You don't have any scheduled exports configured.</p>
                </div>
            `;
        } else {
            const exportsHtml = exports.map(exp => `
                <div style="border: 1px solid #e5e7eb; border-radius: 8px; padding: 1rem; margin-bottom: 1rem;">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
                        <strong>Export ID: ${exp.export_id}</strong>
                        <button class="btn btn-sm btn-danger" onclick="dashboard.cancelScheduledExport('${exp.export_id}')">
                            Cancel
                        </button>
                    </div>
                    <div style="font-size: 0.875rem; color: #6b7280;">
                        <div>Format: ${exp.export_config.format}</div>
                        <div>Frequency: ${exp.schedule.frequency}</div>
                        <div>Next Run: ${new Date(exp.next_run).toLocaleString()}</div>
                    </div>
                </div>
            `).join('');

            modalBody.innerHTML = `
                <div style="padding: 1rem;">
                    <h4 style="margin-bottom: 1rem;">Scheduled Exports</h4>
                    ${exportsHtml}
                </div>
            `;
        }
        
        modal.classList.add('show');
    }

    async cancelScheduledExport(exportId) {
        try {
            const response = await fetch(`${this.apiBase}/export/schedule/${exportId}`, {
                method: 'DELETE',
                headers: {
                    'Authorization': `Bearer ${localStorage.getItem('token')}`
                }
            });

            if (!response.ok) {
                throw new Error(`Failed to cancel export: ${response.statusText}`);
            }

            this.showError('Export cancelled successfully');
            this.closeModal();
            this.showScheduledExports(); // Refresh the list

        } catch (error) {
            console.error('Failed to cancel scheduled export:', error);
            this.showError(`Failed to cancel export: ${error.message}`);
        }
    }

    updateFormatSelection() {
        const format = document.getElementById('exportFormat')?.value;
        const formatCards = document.querySelectorAll('.format-card');
        
        formatCards.forEach(card => {
            card.classList.remove('selected');
            if (card.dataset.format === format) {
                card.classList.add('selected');
            }
        });
    }

    updateColumnSelection() {
        // This could be used to update column preview or validation
        const selectedColumns = document.querySelectorAll('#columnsSelector input[type="checkbox"]:checked');
        console.log(`Selected ${selectedColumns.length} columns for export`);
    }

    async loadExportHistory() {
        try {
            // For now, we'll create some sample export history
            // In a real implementation, this would come from the API
            const sampleHistory = [
                {
                    export_id: 'export_20231201_143022_150',
                    filename: 'compliance_export_20231201_143022.csv',
                    format: 'csv',
                    record_count: 150,
                    created_at: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString()
                },
                {
                    export_id: 'export_20231201_100015_89',
                    filename: 'compliance_export_20231201_100015.xlsx',
                    format: 'excel',
                    record_count: 89,
                    created_at: new Date(Date.now() - 6 * 60 * 60 * 1000).toISOString()
                }
            ];

            this.updateExportHistory(sampleHistory);
        } catch (error) {
            console.error('Failed to load export history:', error);
        }
    }

    updateExportHistory(history) {
        const exportList = document.getElementById('exportList');
        if (!exportList) return;

        if (history.length === 0) {
            exportList.innerHTML = '<div style="text-align: center; padding: 1rem; color: #6b7280;">No export history</div>';
            return;
        }

        const historyHtml = history.map(export => `
            <div class="export-item">
                <div class="export-item-info">
                    <div class="export-item-name">${export.filename}</div>
                    <div class="export-item-details">
                        ${export.format.toUpperCase()} • ${export.record_count} records • ${this.formatRelativeTime(export.created_at)}
                    </div>
                </div>
                <div class="export-item-actions">
                    <button class="export-item-btn download" onclick="dashboard.downloadExport('${export.export_id}')">
                        <i class="fas fa-download"></i> Download
                    </button>
                    <button class="export-item-btn" onclick="dashboard.deleteExport('${export.export_id}')">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
            </div>
        `).join('');

        exportList.innerHTML = historyHtml;
    }

    addToExportHistory(exportResult) {
        const exportList = document.getElementById('exportList');
        if (!exportList) return;

        const historyItem = `
            <div class="export-item">
                <div class="export-item-info">
                    <div class="export-item-name">${exportResult.filename}</div>
                    <div class="export-item-details">
                        ${exportResult.format.toUpperCase()} • ${exportResult.record_count} records • Just now
                    </div>
                </div>
                <div class="export-item-actions">
                    <button class="export-item-btn download" onclick="dashboard.downloadExport('${exportResult.export_id}')">
                        <i class="fas fa-download"></i> Download
                    </button>
                    <button class="export-item-btn" onclick="dashboard.deleteExport('${exportResult.export_id}')">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
            </div>
        `;

        // Add to the beginning of the list
        exportList.insertAdjacentHTML('afterbegin', historyItem);
    }

    async downloadExport(exportId) {
        try {
            // In a real implementation, this would trigger a file download
            this.showError('Download functionality will be implemented in a future update');
        } catch (error) {
            console.error('Download failed:', error);
            this.showError(`Download failed: ${error.message}`);
        }
    }

    async deleteExport(exportId) {
        try {
            // In a real implementation, this would delete the export from history
            this.showError('Delete functionality will be implemented in a future update');
        } catch (error) {
            console.error('Delete failed:', error);
            this.showError(`Delete failed: ${error.message}`);
        }
    }
}

// Initialize dashboard when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.dashboard = new ComplianceDashboard();
}); 