/**
 * Report Analytics & Trend Identification JavaScript
 * 
 * This module provides comprehensive analytics functionality including:
 * - Quick analytics overview
 * - Comprehensive analysis with predictions and anomalies
 * - Trend analysis and pattern identification
 * - Predictive analytics
 * - Anomaly detection
 * - System health scoring
 * - Period comparison analysis
 */

class ReportAnalyticsManager {
    constructor() {
        this.currentTab = 'overview';
        this.initializeEventListeners();
        this.loadAgenciesAndForms();
        this.setDefaultDates();
    }
    
    initializeEventListeners() {
        // Tab switching
        document.querySelectorAll('.analytics-tab').forEach(tab => {
            tab.addEventListener('click', () => {
                this.switchTab(tab.dataset.tab);
            });
        });
    }
    
    switchTab(tabName) {
        // Update active tab
        document.querySelectorAll('.analytics-tab').forEach(tab => {
            tab.classList.remove('active');
        });
        document.querySelector(`[data-tab="${tabName}"]`).classList.add('active');
        
        // Update active content
        document.querySelectorAll('.analytics-content').forEach(content => {
            content.classList.remove('active');
        });
        document.getElementById(`${tabName}-tab`).classList.add('active');
        
        this.currentTab = tabName;
    }
    
    async loadAgenciesAndForms() {
        try {
            // Load agencies
            const agenciesResponse = await fetch('/api/agencies', {
                headers: {
                    'Authorization': `Bearer ${this.getAuthToken()}`
                }
            });
            
            if (agenciesResponse.ok) {
                const agencies = await agenciesResponse.json();
                this.populateSelect('quickAgencies', agencies, 'name', 'id');
                this.populateSelect('compAgencies', agencies, 'name', 'id');
                this.populateSelect('trendAgencies', agencies, 'name', 'id');
                this.populateSelect('predictionAgencies', agencies, 'name', 'id');
                this.populateSelect('anomalyAgencies', agencies, 'name', 'id');
                this.populateSelect('healthAgencies', agencies, 'name', 'id');
                this.populateSelect('comparisonAgencies', agencies, 'name', 'id');
            }
            
            // Load forms (you might need to adjust this endpoint)
            const formsResponse = await fetch('/api/forms', {
                headers: {
                    'Authorization': `Bearer ${this.getAuthToken()}`
                }
            });
            
            if (formsResponse.ok) {
                const forms = await formsResponse.json();
                this.populateSelect('quickForms', forms, 'name', 'name');
                this.populateSelect('compForms', forms, 'name', 'name');
                this.populateSelect('trendForms', forms, 'name', 'name');
                this.populateSelect('predictionForms', forms, 'name', 'name');
                this.populateSelect('anomalyForms', forms, 'name', 'name');
                this.populateSelect('healthForms', forms, 'name', 'name');
                this.populateSelect('comparisonForms', forms, 'name', 'name');
            }
            
        } catch (error) {
            console.error('Error loading agencies and forms:', error);
        }
    }
    
    populateSelect(selectId, data, displayField, valueField) {
        const select = document.getElementById(selectId);
        if (!select) return;
        
        // Clear existing options except the first one
        while (select.children.length > 1) {
            select.removeChild(select.lastChild);
        }
        
        // Add new options
        data.forEach(item => {
            const option = document.createElement('option');
            option.value = item[valueField];
            option.textContent = item[displayField];
            select.appendChild(option);
        });
    }
    
    setDefaultDates() {
        const now = new Date();
        const thirtyDaysAgo = new Date(now.getTime() - (30 * 24 * 60 * 60 * 1000));
        
        // Set default dates for comprehensive analysis
        document.getElementById('compStartDate').value = this.formatDateTimeLocal(thirtyDaysAgo);
        document.getElementById('compEndDate').value = this.formatDateTimeLocal(now);
        
        // Set default dates for period comparison
        const sixtyDaysAgo = new Date(now.getTime() - (60 * 24 * 60 * 60 * 1000));
        const ninetyDaysAgo = new Date(now.getTime() - (90 * 24 * 60 * 60 * 1000));
        
        document.getElementById('period1Start').value = this.formatDateTimeLocal(ninetyDaysAgo);
        document.getElementById('period1End').value = this.formatDateTimeLocal(sixtyDaysAgo);
        document.getElementById('period2Start').value = this.formatDateTimeLocal(thirtyDaysAgo);
        document.getElementById('period2End').value = this.formatDateTimeLocal(now);
    }
    
    formatDateTimeLocal(date) {
        return date.toISOString().slice(0, 16);
    }
    
    getSelectedValues(selectId) {
        const select = document.getElementById(selectId);
        const selectedOptions = Array.from(select.selectedOptions);
        return selectedOptions.map(option => option.value).filter(value => value !== '');
    }
    
    async generateQuickAnalytics() {
        const periodDays = parseInt(document.getElementById('quickPeriod').value);
        const agencies = this.getSelectedValues('quickAgencies');
        const forms = this.getSelectedValues('quickForms');
        
        this.showLoading('quickResults');
        
        try {
            const response = await fetch('/api/reports/analytics/quick', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${this.getAuthToken()}`
                },
                body: JSON.stringify({
                    period_days: periodDays,
                    agencies: agencies.length > 0 ? agencies : null,
                    form_types: forms.length > 0 ? forms : null
                })
            });
            
            if (response.ok) {
                const data = await response.json();
                this.displayQuickAnalytics(data);
            } else {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
        } catch (error) {
            this.showError('quickResults', `Failed to generate quick analytics: ${error.message}`);
        }
    }
    
    displayQuickAnalytics(data) {
        const resultsDiv = document.getElementById('quickResults');
        
        // Update metrics
        document.getElementById('quickTotalChanges').textContent = data.summary.total_changes;
        document.getElementById('quickSuccessRate').textContent = `${data.summary.monitoring_success_rate}%`;
        document.getElementById('quickHealthScore').textContent = data.summary.system_health_score;
        document.getElementById('quickTrendDirection').textContent = data.trend_direction;
        
        // Update insights
        const insightsList = document.getElementById('quickInsights');
        insightsList.innerHTML = '';
        data.key_insights.forEach(insight => {
            const li = document.createElement('li');
            li.textContent = insight;
            insightsList.appendChild(li);
        });
        
        // Update recommendations
        const recommendationsList = document.getElementById('quickRecommendations');
        recommendationsList.innerHTML = '';
        data.recommendations.forEach(recommendation => {
            const li = document.createElement('li');
            li.textContent = recommendation;
            recommendationsList.appendChild(li);
        });
        
        resultsDiv.style.display = 'block';
    }
    
    async generateComprehensiveAnalytics() {
        const startDate = document.getElementById('compStartDate').value;
        const endDate = document.getElementById('compEndDate').value;
        const agencies = this.getSelectedValues('compAgencies');
        const forms = this.getSelectedValues('compForms');
        const includePredictions = document.getElementById('includePredictions').checked;
        const includeAnomalies = document.getElementById('includeAnomalies').checked;
        const includeCorrelations = document.getElementById('includeCorrelations').checked;
        
        this.showLoading('comprehensiveResults');
        
        try {
            const response = await fetch('/api/reports/analytics/comprehensive', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${this.getAuthToken()}`
                },
                body: JSON.stringify({
                    start_date: startDate ? new Date(startDate).toISOString() : null,
                    end_date: endDate ? new Date(endDate).toISOString() : null,
                    agencies: agencies.length > 0 ? agencies : null,
                    form_types: forms.length > 0 ? forms : null,
                    include_predictions: includePredictions,
                    include_anomalies: includeAnomalies,
                    include_correlations: includeCorrelations
                })
            });
            
            if (response.ok) {
                const data = await response.json();
                this.displayComprehensiveAnalytics(data);
            } else {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
        } catch (error) {
            this.showError('comprehensiveResults', `Failed to generate comprehensive analytics: ${error.message}`);
        }
    }
    
    displayComprehensiveAnalytics(data) {
        const resultsDiv = document.getElementById('comprehensiveResults');
        
        // Create comprehensive results display
        let html = `
            <div class="analytics-grid">
                <div class="analytics-card">
                    <h3>Total Changes</h3>
                    <div class="metric-value">${data.change_analytics.total_changes}</div>
                    <div class="metric-label">Changes detected in period</div>
                </div>
                <div class="analytics-card">
                    <h3>Success Rate</h3>
                    <div class="metric-value">${data.performance_analytics.success_rate}%</div>
                    <div class="metric-label">Monitoring success rate</div>
                </div>
                <div class="analytics-card">
                    <h3>Health Score</h3>
                    <div class="metric-value">${data.summary.system_health_score}</div>
                    <div class="metric-label">System health score</div>
                </div>
                <div class="analytics-card">
                    <h3>Trend Direction</h3>
                    <div class="metric-value">${data.trend_analysis.trend_direction}</div>
                    <div class="metric-label">Change trend direction</div>
                </div>
            </div>
            
            <div class="chart-container">
                <h3>Key Insights</h3>
                <ul class="insights-list">
                    ${data.insights.map(insight => `<li>${insight}</li>`).join('')}
                </ul>
            </div>
            
            <div class="chart-container">
                <h3>Recommendations</h3>
                <ul class="recommendations-list">
                    ${data.recommendations.map(rec => `<li>${rec}</li>`).join('')}
                </ul>
            </div>
        `;
        
        // Add predictions if included
        if (data.predictions && Object.keys(data.predictions).length > 0) {
            html += `
                <div class="chart-container">
                    <h3>Predictions</h3>
                    <div class="analytics-grid">
                        <div class="analytics-card">
                            <h4>Next Week</h4>
                            <div class="metric-value">${data.predictions.predicted_changes_next_week}</div>
                        </div>
                        <div class="analytics-card">
                            <h4>Next Month</h4>
                            <div class="metric-value">${data.predictions.predicted_changes_next_month}</div>
                        </div>
                        <div class="analytics-card">
                            <h4>Confidence</h4>
                            <div class="metric-value">${data.predictions.prediction_confidence}</div>
                        </div>
                    </div>
                </div>
            `;
        }
        
        // Add anomalies if included
        if (data.anomalies && data.anomalies.anomalies_detected > 0) {
            html += `
                <div class="chart-container">
                    <h3>Anomalies Detected</h3>
                    <div class="analytics-grid">
                        <div class="analytics-card">
                            <h4>Total Anomalies</h4>
                            <div class="metric-value">${data.anomalies.anomalies_detected}</div>
                        </div>
                        <div class="analytics-card">
                            <h4>Spike Anomalies</h4>
                            <div class="metric-value">${data.anomalies.anomaly_types.spike || 0}</div>
                        </div>
                        <div class="analytics-card">
                            <h4>Drop Anomalies</h4>
                            <div class="metric-value">${data.anomalies.anomaly_types.drop || 0}</div>
                        </div>
                    </div>
                </div>
            `;
        }
        
        resultsDiv.innerHTML = html;
        resultsDiv.style.display = 'block';
    }
    
    async generateTrendAnalysis() {
        const period = document.getElementById('trendPeriod').value;
        const agencies = this.getSelectedValues('trendAgencies');
        const forms = this.getSelectedValues('trendForms');
        
        this.showLoading('trendResults');
        
        try {
            const response = await fetch(`/api/reports/analytics/trends/${period}?` + new URLSearchParams({
                agencies: agencies.join(','),
                form_types: forms.join(',')
            }), {
                headers: {
                    'Authorization': `Bearer ${this.getAuthToken()}`
                }
            });
            
            if (response.ok) {
                const data = await response.json();
                this.displayTrendAnalysis(data);
            } else {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
        } catch (error) {
            this.showError('trendResults', `Failed to generate trend analysis: ${error.message}`);
        }
    }
    
    displayTrendAnalysis(data) {
        const resultsDiv = document.getElementById('trendResults');
        
        // Update metrics
        document.getElementById('trendDirection').textContent = data.trend_analysis.trend_direction;
        document.getElementById('trendStrength').textContent = data.trend_analysis.trend_strength;
        document.getElementById('trendPercentage').textContent = `${data.trend_analysis.trend_percentage}%`;
        document.getElementById('volatilityScore').textContent = data.trend_analysis.volatility_score;
        
        // Create simple chart (you can integrate with Chart.js or similar)
        const chartDiv = document.getElementById('trendChart');
        if (data.trend_analysis.daily_data) {
            const chartData = Object.entries(data.trend_analysis.daily_data);
            chartDiv.innerHTML = `
                <div style="height: 300px; overflow-y: auto;">
                    <h4>Daily Change Counts</h4>
                    ${chartData.map(([date, count]) => `
                        <div style="display: flex; justify-content: space-between; padding: 5px 0; border-bottom: 1px solid #eee;">
                            <span>${date}</span>
                            <span style="font-weight: bold; color: #667eea;">${count}</span>
                        </div>
                    `).join('')}
                </div>
            `;
        }
        
        resultsDiv.style.display = 'block';
    }
    
    async generatePredictions() {
        const daysAhead = parseInt(document.getElementById('predictionDays').value);
        const agencies = this.getSelectedValues('predictionAgencies');
        const forms = this.getSelectedValues('predictionForms');
        
        this.showLoading('predictionResults');
        
        try {
            const response = await fetch('/api/reports/analytics/predictions?' + new URLSearchParams({
                days_ahead: daysAhead,
                agencies: agencies.join(','),
                form_types: forms.join(',')
            }), {
                headers: {
                    'Authorization': `Bearer ${this.getAuthToken()}`
                }
            });
            
            if (response.ok) {
                const data = await response.json();
                this.displayPredictions(data);
            } else {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
        } catch (error) {
            this.showError('predictionResults', `Failed to generate predictions: ${error.message}`);
        }
    }
    
    displayPredictions(data) {
        const resultsDiv = document.getElementById('predictionResults');
        
        // Update metrics
        document.getElementById('predictionWeek').textContent = data.predicted_changes_next_week;
        document.getElementById('predictionMonth').textContent = data.predicted_changes_next_month;
        document.getElementById('predictionConfidence').textContent = data.prediction_confidence;
        document.getElementById('confidenceInterval').textContent = 
            `${data.confidence_intervals.next_week.lower} - ${data.confidence_intervals.next_week.upper}`;
        
        // Update prediction factors
        const factorsList = document.getElementById('predictionFactors');
        factorsList.innerHTML = '';
        data.prediction_factors.forEach(factor => {
            const li = document.createElement('li');
            li.textContent = factor;
            factorsList.appendChild(li);
        });
        
        resultsDiv.style.display = 'block';
    }
    
    async detectAnomalies() {
        const agencies = this.getSelectedValues('anomalyAgencies');
        const forms = this.getSelectedValues('anomalyForms');
        
        this.showLoading('anomalyResults');
        
        try {
            const response = await fetch('/api/reports/analytics/anomalies?' + new URLSearchParams({
                agencies: agencies.join(','),
                form_types: forms.join(',')
            }), {
                headers: {
                    'Authorization': `Bearer ${this.getAuthToken()}`
                }
            });
            
            if (response.ok) {
                const data = await response.json();
                this.displayAnomalies(data);
            } else {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
        } catch (error) {
            this.showError('anomalyResults', `Failed to detect anomalies: ${error.message}`);
        }
    }
    
    displayAnomalies(data) {
        const resultsDiv = document.getElementById('anomalyResults');
        
        // Update metrics
        document.getElementById('anomalyCount').textContent = data.anomalies_detected;
        document.getElementById('spikeAnomalies').textContent = data.anomaly_types.spike || 0;
        document.getElementById('dropAnomalies').textContent = data.anomaly_types.drop || 0;
        document.getElementById('highSeverityAnomalies').textContent = data.anomaly_severity.high || 0;
        
        // Display anomaly details
        const detailsDiv = document.getElementById('anomalyDetails');
        if (data.anomaly_details && data.anomaly_details.length > 0) {
            detailsDiv.innerHTML = data.anomaly_details.map(anomaly => `
                <div class="anomaly-item">
                    <div class="anomaly-date">${anomaly.date}</div>
                    <div class="anomaly-details">
                        Value: ${anomaly.value} | Z-Score: ${anomaly.z_score} | Expected Range: ${anomaly.expected_range}
                    </div>
                </div>
            `).join('');
        } else {
            detailsDiv.innerHTML = '<p>No anomalies detected in the specified period.</p>';
        }
        
        resultsDiv.style.display = 'block';
    }
    
    async generateHealthScore() {
        const days = parseInt(document.getElementById('healthDays').value);
        const agencies = this.getSelectedValues('healthAgencies');
        const forms = this.getSelectedValues('healthForms');
        
        this.showLoading('healthResults');
        
        try {
            const response = await fetch('/api/reports/analytics/health-score?' + new URLSearchParams({
                days: days,
                agencies: agencies.join(','),
                form_types: forms.join(',')
            }), {
                headers: {
                    'Authorization': `Bearer ${this.getAuthToken()}`
                }
            });
            
            if (response.ok) {
                const data = await response.json();
                this.displayHealthScore(data);
            } else {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
        } catch (error) {
            this.showError('healthResults', `Failed to generate health score: ${error.message}`);
        }
    }
    
    displayHealthScore(data) {
        const resultsDiv = document.getElementById('healthResults');
        
        // Update health score circle
        const scoreValue = document.getElementById('healthScoreValue');
        const scoreCircle = document.getElementById('healthScoreCircle');
        
        scoreValue.textContent = data.overall_score;
        
        // Update circle color based on score
        scoreCircle.className = 'health-score-circle';
        if (data.overall_score >= 80) {
            scoreCircle.classList.add('health-excellent');
        } else if (data.overall_score >= 60) {
            scoreCircle.classList.add('health-good');
        } else {
            scoreCircle.classList.add('health-poor');
        }
        
        // Update component scores
        document.getElementById('performanceScore').textContent = data.performance_score;
        document.getElementById('changeManagementScore').textContent = data.change_management_score;
        document.getElementById('impactManagementScore').textContent = data.impact_management_score;
        
        // Update recommendations
        const recommendationsList = document.getElementById('healthRecommendations');
        recommendationsList.innerHTML = '';
        data.recommendations.forEach(recommendation => {
            const li = document.createElement('li');
            li.textContent = recommendation;
            recommendationsList.appendChild(li);
        });
        
        resultsDiv.style.display = 'block';
    }
    
    async comparePeriods() {
        const period1Start = document.getElementById('period1Start').value;
        const period1End = document.getElementById('period1End').value;
        const period2Start = document.getElementById('period2Start').value;
        const period2End = document.getElementById('period2End').value;
        const agencies = this.getSelectedValues('comparisonAgencies');
        const forms = this.getSelectedValues('comparisonForms');
        
        this.showLoading('comparisonResults');
        
        try {
            const response = await fetch('/api/reports/analytics/trend-comparison', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${this.getAuthToken()}`
                },
                body: JSON.stringify({
                    period1_start: new Date(period1Start).toISOString(),
                    period1_end: new Date(period1End).toISOString(),
                    period2_start: new Date(period2Start).toISOString(),
                    period2_end: new Date(period2End).toISOString(),
                    agencies: agencies.length > 0 ? agencies : null,
                    form_types: forms.length > 0 ? forms : null
                })
            });
            
            if (response.ok) {
                const data = await response.json();
                this.displayPeriodComparison(data);
            } else {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
        } catch (error) {
            this.showError('comparisonResults', `Failed to compare periods: ${error.message}`);
        }
    }
    
    displayPeriodComparison(data) {
        const resultsDiv = document.getElementById('comparisonResults');
        
        // Update metrics
        document.getElementById('healthScoreChange').textContent = data.comparison.health_score_change;
        document.getElementById('successRateChange').textContent = `${data.comparison.success_rate_change}%`;
        document.getElementById('totalChangesChange').textContent = data.comparison.total_changes_change;
        document.getElementById('impactScoreChange').textContent = data.comparison.impact_score_change;
        
        // Update insights
        const insightsList = document.getElementById('comparisonInsights');
        insightsList.innerHTML = '';
        data.insights.forEach(insight => {
            const li = document.createElement('li');
            li.textContent = insight;
            insightsList.appendChild(li);
        });
        
        resultsDiv.style.display = 'block';
    }
    
    showLoading(containerId) {
        const container = document.getElementById(containerId);
        container.innerHTML = '<div class="loading">Generating analytics...</div>';
        container.style.display = 'block';
    }
    
    showError(containerId, message) {
        const container = document.getElementById(containerId);
        container.innerHTML = `<div class="error-message">${message}</div>`;
        container.style.display = 'block';
    }
    
    getAuthToken() {
        return localStorage.getItem('authToken') || '';
    }
}

// Initialize the analytics manager when the page loads
let analyticsManager;
document.addEventListener('DOMContentLoaded', () => {
    analyticsManager = new ReportAnalyticsManager();
}); 