"""
Unit tests for Enhanced Monitoring Scheduler

Tests the enhanced scheduler with AI-powered monitoring and frequency management
for daily/weekly monitoring based on form requirements.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, timezone, timedelta
from typing import Dict, Any

from .enhanced_scheduler import (
    EnhancedMonitoringScheduler, get_enhanced_scheduler,
    start_enhanced_scheduler, stop_enhanced_scheduler
)
from ..database.models import Agency, Form, FormChange, MonitoringRun
from ..monitors.ai_enhanced_monitor import AIEnhancedMonitor


class TestEnhancedMonitoringScheduler:
    """Test suite for Enhanced Monitoring Scheduler."""
    
    @pytest.fixture
    def mock_ai_monitor(self):
        """Mock AI-enhanced monitor for testing."""
        mock_monitor = Mock(spec=AIEnhancedMonitor)
        mock_monitor.monitor_agency_with_ai = AsyncMock()
        mock_monitor.get_service_health = AsyncMock()
        mock_monitor.analysis_service = Mock()
        mock_monitor.analysis_service.get_service_stats = Mock(return_value={})
        return mock_monitor
    
    @pytest.fixture
    def mock_notification_manager(self):
        """Mock notification manager for testing."""
        mock_notifier = Mock()
        mock_notifier.send_change_notification = AsyncMock()
        return mock_notifier
    
    @pytest.fixture
    def sample_agency(self):
        """Sample agency for testing."""
        agency = Mock(spec=Agency)
        agency.id = 1
        agency.name = "Test Department of Labor"
        agency.is_active = True
        return agency
    
    @pytest.fixture
    def sample_form(self, sample_agency):
        """Sample form for testing."""
        form = Mock(spec=Form)
        form.id = 1
        form.name = "WH-347"
        form.title = "Statement of Compliance"
        form.is_active = True
        form.agency = sample_agency
        form.agency_id = sample_agency.id
        form.check_frequency = "daily"
        form.last_checked = None
        return form
    
    @pytest.fixture
    def sample_form_change(self, sample_form):
        """Sample form change for testing."""
        change = Mock(spec=FormChange)
        change.id = 1
        change.form_id = sample_form.id
        change.form = sample_form
        change.detected_at = datetime.now(timezone.utc)
        change.severity = "high"
        change.ai_confidence_score = 85
        change.ai_change_category = "form_update"
        change.is_cosmetic_change = False
        return change
    
    @pytest.fixture
    def scheduler(self, mock_ai_monitor, mock_notification_manager):
        """Enhanced scheduler instance for testing."""
        with patch('src.scheduler.enhanced_scheduler.AIEnhancedMonitor', return_value=mock_ai_monitor), \
             patch('src.scheduler.enhanced_scheduler.NotificationManager', return_value=mock_notification_manager):
            return EnhancedMonitoringScheduler(
                confidence_threshold=70,
                enable_llm_analysis=True,
                batch_size=3
            )
    
    def test_scheduler_initialization(self, mock_ai_monitor, mock_notification_manager):
        """Test scheduler initialization with various configurations."""
        with patch('src.scheduler.enhanced_scheduler.AIEnhancedMonitor', return_value=mock_ai_monitor), \
             patch('src.scheduler.enhanced_scheduler.NotificationManager', return_value=mock_notification_manager):
            
            scheduler = EnhancedMonitoringScheduler(
                confidence_threshold=80,
                enable_llm_analysis=False,
                batch_size=5
            )
            
            assert scheduler.ai_monitor == mock_ai_monitor
            assert scheduler.notification_manager == mock_notification_manager
            assert scheduler.confidence_threshold == 80
            assert scheduler.enable_llm_analysis == False
            assert scheduler.batch_size == 5
            assert scheduler.running == False
            assert isinstance(scheduler.stats, dict)
            assert isinstance(scheduler.frequency_settings, dict)
    
    def test_frequency_settings_configuration(self, scheduler):
        """Test frequency settings are properly configured."""
        settings = scheduler.frequency_settings
        
        assert "daily" in settings
        assert "weekly" in settings
        assert "monthly" in settings
        
        # Check daily settings
        daily_settings = settings["daily"]
        assert daily_settings["time"] == "06:00"
        assert daily_settings["priority"] == "high"
        assert daily_settings["max_retries"] == 3
        
        # Check weekly settings
        weekly_settings = settings["weekly"]
        assert weekly_settings["time"] == "07:00"
        assert weekly_settings["day"] == "monday"
        assert weekly_settings["priority"] == "medium"
        assert weekly_settings["max_retries"] == 2
        
        # Check monthly settings
        monthly_settings = settings["monthly"]
        assert monthly_settings["time"] == "06:30"
        assert monthly_settings["day"] == "monday"
        assert monthly_settings["priority"] == "low"
        assert monthly_settings["max_retries"] == 1
    
    def test_scheduler_start_stop(self, scheduler):
        """Test scheduler start and stop functionality."""
        # Test start
        with patch('threading.Thread') as mock_thread:
            scheduler.start()
            
            assert scheduler.running == True
            mock_thread.assert_called_once()
            
            # Test stop
            scheduler.stop()
            assert scheduler.running == False
    
    def test_scheduler_already_running(self, scheduler):
        """Test scheduler behavior when already running."""
        scheduler.running = True
        
        with patch('threading.Thread') as mock_thread:
            scheduler.start()
            
            # Should not start again
            mock_thread.assert_not_called()
    
    def test_scheduler_not_running_stop(self, scheduler):
        """Test scheduler stop when not running."""
        scheduler.running = False
        
        scheduler.stop()
        
        # Should handle gracefully
        assert scheduler.running == False
    
    @pytest.mark.asyncio
    async def test_ai_monitor_single_form_success(self, scheduler, sample_agency, sample_form, sample_form_change):
        """Test successful AI monitoring of a single form."""
        # Setup mocks
        sample_agency.forms = [sample_form]
        
        with patch('src.scheduler.enhanced_scheduler.get_db') as mock_get_db:
            mock_db = Mock()
            mock_db.query.return_value.filter.return_value.first.side_effect = [sample_agency, sample_form]
            mock_db.commit = Mock()
            mock_get_db.return_value.__enter__.return_value = mock_db
            
            # Mock AI monitoring result
            ai_result = {
                "changes_detected": 1,
                "ai_analyses_performed": 1,
                "analysis_summary": {
                    "avg_confidence_score": 85
                }
            }
            scheduler.ai_monitor.monitor_agency_with_ai.return_value = ai_result
            
            # Mock form change query
            mock_db.query.return_value.filter.return_value.order_by.return_value.first.return_value = sample_form_change
            
            # Execute monitoring
            result = await scheduler._ai_monitor_single_form(sample_agency.id, sample_form.id, "daily")
            
            # Verify results
            assert result == ai_result
            scheduler.ai_monitor.monitor_agency_with_ai.assert_called_once_with(sample_agency.id)
            mock_db.commit.assert_called()
    
    @pytest.mark.asyncio
    async def test_ai_monitor_single_form_no_changes(self, scheduler, sample_agency, sample_form):
        """Test AI monitoring when no changes are detected."""
        sample_agency.forms = [sample_form]
        
        with patch('src.scheduler.enhanced_scheduler.get_db') as mock_get_db:
            mock_db = Mock()
            mock_db.query.return_value.filter.return_value.first.side_effect = [sample_agency, sample_form]
            mock_db.commit = Mock()
            mock_get_db.return_value.__enter__.return_value = mock_db
            
            # Mock AI monitoring result with no changes
            ai_result = {
                "changes_detected": 0,
                "ai_analyses_performed": 0,
                "analysis_summary": {
                    "avg_confidence_score": 0
                }
            }
            scheduler.ai_monitor.monitor_agency_with_ai.return_value = ai_result
            
            # Execute monitoring
            result = await scheduler._ai_monitor_single_form(sample_agency.id, sample_form.id, "weekly")
            
            # Verify results
            assert result == ai_result
            # Should not send notifications when no changes detected
            scheduler.notification_manager.send_change_notification.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_ai_monitor_single_form_agency_not_found(self, scheduler):
        """Test AI monitoring when agency is not found."""
        with patch('src.scheduler.enhanced_scheduler.get_db') as mock_get_db:
            mock_db = Mock()
            mock_db.query.return_value.filter.return_value.first.return_value = None
            mock_get_db.return_value.__enter__.return_value = mock_db
            
            result = await scheduler._ai_monitor_single_form(999, 1, "daily")
            
            assert result is None
            scheduler.ai_monitor.monitor_agency_with_ai.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_ai_monitor_single_form_ai_failure(self, scheduler, sample_agency, sample_form):
        """Test AI monitoring when AI service fails."""
        sample_agency.forms = [sample_form]
        
        with patch('src.scheduler.enhanced_scheduler.get_db') as mock_get_db:
            mock_db = Mock()
            mock_db.query.return_value.filter.return_value.first.side_effect = [sample_agency, sample_form]
            mock_get_db.return_value.__enter__.return_value = mock_db
            
            # Mock AI monitoring failure
            scheduler.ai_monitor.monitor_agency_with_ai.side_effect = Exception("AI service error")
            
            result = await scheduler._ai_monitor_single_form(sample_agency.id, sample_form.id, "daily")
            
            assert result is None
    
    @pytest.mark.asyncio
    async def test_send_ai_enhanced_notifications(self, scheduler, sample_form_change):
        """Test sending AI-enhanced notifications."""
        with patch('src.scheduler.enhanced_scheduler.get_db') as mock_get_db:
            mock_db = Mock()
            mock_db.query.return_value.filter.return_value.order_by.return_value.first.return_value = sample_form_change
            mock_get_db.return_value.__enter__.return_value = mock_db
            
            ai_result = {"changes_detected": 1}
            
            await scheduler._send_ai_enhanced_notifications(sample_form_change.form_id, ai_result, mock_db)
            
            scheduler.notification_manager.send_change_notification.assert_called_once_with(sample_form_change.id)
    
    @pytest.mark.asyncio
    async def test_consider_frequency_adjustment_high_activity(self, scheduler, sample_form):
        """Test frequency adjustment for high activity forms."""
        ai_result = {
            "changes_detected": 3,
            "analysis_summary": {
                "avg_confidence_score": 90
            }
        }
        
        with patch.object(scheduler, '_suggest_frequency_change', new_callable=AsyncMock) as mock_suggest:
            await scheduler._consider_frequency_adjustment(sample_form, ai_result, "weekly")
            
            # Should suggest daily monitoring for high activity
            mock_suggest.assert_called_once_with(sample_form.id, "daily", "high_activity")
    
    @pytest.mark.asyncio
    async def test_consider_frequency_adjustment_low_activity(self, scheduler, sample_form):
        """Test frequency adjustment for low activity forms."""
        ai_result = {
            "changes_detected": 0,
            "analysis_summary": {
                "avg_confidence_score": 50
            }
        }
        
        with patch.object(scheduler, '_suggest_frequency_change', new_callable=AsyncMock) as mock_suggest:
            await scheduler._consider_frequency_adjustment(sample_form, ai_result, "daily")
            
            # Should suggest weekly monitoring for low activity
            mock_suggest.assert_called_once_with(sample_form.id, "weekly", "low_activity")
    
    @pytest.mark.asyncio
    async def test_consider_frequency_adjustment_no_change_needed(self, scheduler, sample_form):
        """Test frequency adjustment when no change is needed."""
        ai_result = {
            "changes_detected": 1,
            "analysis_summary": {
                "avg_confidence_score": 75
            }
        }
        
        with patch.object(scheduler, '_suggest_frequency_change', new_callable=AsyncMock) as mock_suggest:
            await scheduler._consider_frequency_adjustment(sample_form, ai_result, "weekly")
            
            # Should not suggest any change for moderate activity
            mock_suggest.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_suggest_frequency_change(self, scheduler):
        """Test frequency change suggestion."""
        await scheduler._suggest_frequency_change(1, "daily", "high_activity")
        
        # Should log the suggestion
        # In a real implementation, this would create a suggestion record
    
    def test_check_monthly_schedule_first_monday(self, scheduler):
        """Test monthly schedule check on first Monday."""
        with patch('datetime.datetime') as mock_datetime:
            # Mock first Monday of the month
            mock_date = Mock()
            mock_date.weekday.return_value = 0  # Monday
            mock_date.day = 1  # First day of month
            mock_datetime.now.return_value.date.return_value = mock_date
            
            with patch.object(scheduler, '_ai_monitor_form_wrapper') as mock_wrapper:
                scheduler._check_monthly_schedule(1, 1)
                
                # Should run monthly monitoring
                mock_wrapper.assert_called_once_with(1, 1, "monthly")
    
    def test_check_monthly_schedule_not_first_monday(self, scheduler):
        """Test monthly schedule check when not first Monday."""
        with patch('datetime.datetime') as mock_datetime:
            # Mock second Monday of the month
            mock_date = Mock()
            mock_date.weekday.return_value = 0  # Monday
            mock_date.day = 8  # Second week
            mock_datetime.now.return_value.date.return_value = mock_date
            
            with patch.object(scheduler, '_ai_monitor_form_wrapper') as mock_wrapper:
                scheduler._check_monthly_schedule(1, 1)
                
                # Should not run monthly monitoring
                mock_wrapper.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_generate_enhanced_daily_summary(self, scheduler, sample_form_change):
        """Test enhanced daily summary generation."""
        with patch('src.scheduler.enhanced_scheduler.get_db') as mock_get_db:
            mock_db = Mock()
            mock_db.query.return_value.filter.return_value.all.return_value = [sample_form_change]
            mock_get_db.return_value.__enter__.return_value = mock_db
            
            await scheduler._generate_enhanced_daily_summary()
            
            # Should generate summary with AI insights
            # Verify the summary structure is correct
    
    @pytest.mark.asyncio
    async def test_generate_enhanced_weekly_report(self, scheduler, sample_form_change):
        """Test enhanced weekly report generation."""
        with patch('src.scheduler.enhanced_scheduler.get_db') as mock_get_db:
            mock_db = Mock()
            mock_db.query.return_value.filter.return_value.all.return_value = [sample_form_change]
            mock_get_db.return_value.__enter__.return_value = mock_db
            
            await scheduler._generate_enhanced_weekly_report()
            
            # Should generate comprehensive weekly report
            # Verify the report structure is correct
    
    @pytest.mark.asyncio
    async def test_monitor_ai_performance(self, scheduler, mock_ai_monitor):
        """Test AI performance monitoring."""
        mock_ai_monitor.get_service_health.return_value = {"status": "healthy"}
        
        await scheduler._monitor_ai_performance()
        
        mock_ai_monitor.get_service_health.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_monitor_ai_performance_degraded(self, scheduler, mock_ai_monitor):
        """Test AI performance monitoring when service is degraded."""
        mock_ai_monitor.get_service_health.return_value = {"status": "degraded"}
        
        await scheduler._monitor_ai_performance()
        
        # Should log warning for degraded service
        mock_ai_monitor.get_service_health.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_optimize_monitoring_frequencies(self, scheduler, sample_form):
        """Test monitoring frequency optimization."""
        with patch('src.scheduler.enhanced_scheduler.get_db') as mock_get_db:
            mock_db = Mock()
            mock_db.query.return_value.filter.return_value.all.return_value = [sample_form]
            mock_db.query.return_value.filter.return_value.all.return_value = []  # No recent changes
            mock_get_db.return_value.__enter__.return_value = mock_db
            
            await scheduler._optimize_monitoring_frequencies()
            
            # Should analyze change patterns and suggest optimizations
    
    def test_cleanup_old_data(self, scheduler):
        """Test cleanup of old monitoring data."""
        with patch('src.scheduler.enhanced_scheduler.get_db') as mock_get_db:
            mock_db = Mock()
            old_run = Mock(spec=MonitoringRun)
            mock_db.query.return_value.filter.return_value.all.return_value = [old_run]
            mock_db.delete = Mock()
            mock_db.commit = Mock()
            mock_get_db.return_value.__enter__.return_value = mock_db
            
            scheduler._cleanup_old_data()
            
            mock_db.delete.assert_called_once_with(old_run)
            mock_db.commit.assert_called_once()
    
    def test_update_stats(self, scheduler):
        """Test statistics update."""
        initial_stats = scheduler.stats.copy()
        
        # Test successful run
        scheduler._update_stats(True, 1000, {"changes_detected": 2, "ai_analyses_performed": 1})
        
        assert scheduler.stats["total_runs"] == initial_stats["total_runs"] + 1
        assert scheduler.stats["successful_runs"] == initial_stats["successful_runs"] + 1
        assert scheduler.stats["changes_detected"] == initial_stats["changes_detected"] + 2
        assert scheduler.stats["ai_analyses_performed"] == initial_stats["ai_analyses_performed"] + 1
        
        # Test failed run
        scheduler._update_stats(False, 500, None)
        
        assert scheduler.stats["total_runs"] == initial_stats["total_runs"] + 2
        assert scheduler.stats["failed_runs"] == initial_stats["failed_runs"] + 1
    
    def test_get_enhanced_schedule_status(self, scheduler, mock_ai_monitor):
        """Test enhanced schedule status retrieval."""
        mock_ai_monitor.get_service_health.return_value = {"status": "healthy"}
        
        status = scheduler.get_enhanced_schedule_status()
        
        assert "scheduler_running" in status
        assert "ai_monitor_available" in status
        assert "performance_stats" in status
        assert "frequency_settings" in status
        assert "ai_service_health" in status
    
    def test_reschedule_form_with_ai_success(self, scheduler, sample_form):
        """Test successful form rescheduling with AI."""
        with patch('src.scheduler.enhanced_scheduler.get_db') as mock_get_db, \
             patch('schedule.clear') as mock_clear:
            mock_db = Mock()
            mock_db.query.return_value.filter.return_value.first.return_value = sample_form
            mock_db.commit = Mock()
            mock_get_db.return_value.__enter__.return_value = mock_db
            
            result = scheduler.reschedule_form_with_ai(sample_form.id, "weekly")
            
            assert result == True
            mock_db.commit.assert_called_once()
            mock_clear.assert_called_once()
    
    def test_reschedule_form_with_ai_form_not_found(self, scheduler):
        """Test form rescheduling when form is not found."""
        with patch('src.scheduler.enhanced_scheduler.get_db') as mock_get_db:
            mock_db = Mock()
            mock_db.query.return_value.filter.return_value.first.return_value = None
            mock_get_db.return_value.__enter__.return_value = mock_db
            
            result = scheduler.reschedule_form_with_ai(999, "weekly")
            
            assert result == False
    
    @pytest.mark.asyncio
    async def test_run_immediate_ai_check_single_agency(self, scheduler, mock_ai_monitor):
        """Test immediate AI check for single agency."""
        mock_ai_monitor.monitor_agency_with_ai.return_value = {"status": "success"}
        
        result = await scheduler.run_immediate_ai_check(agency_id=1)
        
        assert result == {"status": "success"}
        mock_ai_monitor.monitor_agency_with_ai.assert_called_once_with(1)
    
    @pytest.mark.asyncio
    async def test_run_immediate_ai_check_all_agencies(self, scheduler, mock_ai_monitor, sample_agency):
        """Test immediate AI check for all agencies."""
        with patch('src.scheduler.enhanced_scheduler.get_db') as mock_get_db:
            mock_db = Mock()
            mock_db.query.return_value.filter.return_value.all.return_value = [sample_agency]
            mock_get_db.return_value.__enter__.return_value = mock_db
            
            mock_ai_monitor.monitor_agency_with_ai.return_value = {"status": "success"}
            
            result = await scheduler.run_immediate_ai_check()
            
            assert result == {sample_agency.id: {"status": "success"}}
            mock_ai_monitor.monitor_agency_with_ai.assert_called_once_with(sample_agency.id)


class TestGlobalSchedulerFunctions:
    """Test suite for global scheduler functions."""
    
    def test_get_enhanced_scheduler_singleton(self):
        """Test that get_enhanced_scheduler returns singleton instance."""
        scheduler1 = get_enhanced_scheduler()
        scheduler2 = get_enhanced_scheduler()
        
        assert scheduler1 is scheduler2
    
    def test_start_enhanced_scheduler(self):
        """Test start_enhanced_scheduler function."""
        with patch('src.scheduler.enhanced_scheduler.get_enhanced_scheduler') as mock_get_scheduler:
            mock_scheduler = Mock()
            mock_get_scheduler.return_value = mock_scheduler
            
            start_enhanced_scheduler()
            
            mock_scheduler.start.assert_called_once()
    
    def test_stop_enhanced_scheduler(self):
        """Test stop_enhanced_scheduler function."""
        with patch('src.scheduler.enhanced_scheduler.get_enhanced_scheduler') as mock_get_scheduler:
            mock_scheduler = Mock()
            mock_get_scheduler.return_value = mock_scheduler
            
            stop_enhanced_scheduler()
            
            mock_scheduler.stop.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__]) 