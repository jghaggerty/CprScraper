"""
Unit tests for Real-time API functionality

Tests WebSocket connections, real-time updates, monitoring status,
and live statistics functionality.
"""

import pytest
import asyncio
import json
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient
from fastapi import WebSocket

from src.api.realtime import (
    ConnectionManager, 
    manager, 
    websocket_endpoint,
    handle_client_request,
    get_recent_changes_for_realtime,
    get_active_alerts_for_realtime,
    broadcast_monitoring_event
)
from src.monitors.monitoring_statistics import MonitoringStatistics
from src.scheduler.enhanced_scheduler import EnhancedMonitoringScheduler


class TestConnectionManager:
    """Test the ConnectionManager class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.manager = ConnectionManager()
        self.mock_websocket = Mock(spec=WebSocket)
        self.mock_websocket.send_text = AsyncMock()
        self.mock_websocket.accept = AsyncMock()
    
    @pytest.mark.asyncio
    async def test_connect(self):
        """Test WebSocket connection."""
        await self.manager.connect(self.mock_websocket, "test_client")
        
        assert self.mock_websocket in self.manager.active_connections
        assert self.mock_websocket in self.manager.connection_metadata
        assert self.manager.connection_metadata[self.mock_websocket]["client_type"] == "test_client"
        self.mock_websocket.accept.assert_called_once()
        self.mock_websocket.send_text.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_disconnect(self):
        """Test WebSocket disconnection."""
        await self.manager.connect(self.mock_websocket, "test_client")
        initial_count = len(self.manager.active_connections)
        
        self.manager.disconnect(self.mock_websocket)
        
        assert self.mock_websocket not in self.manager.active_connections
        assert self.mock_websocket not in self.manager.connection_metadata
        assert len(self.manager.active_connections) == initial_count - 1
    
    @pytest.mark.asyncio
    async def test_broadcast(self):
        """Test broadcasting messages to all connections."""
        # Add multiple connections
        websocket1 = Mock(spec=WebSocket)
        websocket1.send_text = AsyncMock()
        websocket2 = Mock(spec=WebSocket)
        websocket2.send_text = AsyncMock()
        
        await self.manager.connect(websocket1, "client1")
        await self.manager.connect(websocket2, "client2")
        
        message = {"type": "test", "data": "test_message"}
        await self.manager.broadcast(message)
        
        # Both connections should receive the message
        websocket1.send_text.assert_called_once()
        websocket2.send_text.assert_called_once()
        
        # Verify the message content
        sent_message1 = json.loads(websocket1.send_text.call_args[0][0])
        sent_message2 = json.loads(websocket2.send_text.call_args[0][0])
        assert sent_message1 == message
        assert sent_message2 == message
    
    @pytest.mark.asyncio
    async def test_broadcast_empty_connections(self):
        """Test broadcasting with no active connections."""
        message = {"type": "test", "data": "test_message"}
        
        # Should not raise any exceptions
        await self.manager.broadcast(message)
    
    @pytest.mark.asyncio
    async def test_broadcast_with_disconnected_connection(self):
        """Test broadcasting when some connections are disconnected."""
        # Add a connection
        await self.manager.connect(self.mock_websocket, "test_client")
        
        # Simulate a disconnected connection by making send_text raise an exception
        self.mock_websocket.send_text.side_effect = Exception("Connection lost")
        
        message = {"type": "test", "data": "test_message"}
        await self.manager.broadcast(message)
        
        # The disconnected connection should be removed
        assert self.mock_websocket not in self.manager.active_connections
    
    @pytest.mark.asyncio
    async def test_get_current_monitoring_status(self):
        """Test getting current monitoring status."""
        with patch('src.api.realtime.get_db') as mock_get_db:
            mock_db = Mock()
            mock_get_db.return_value.__enter__.return_value = mock_db
            
            # Mock database queries
            mock_db.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = []
            mock_db.query.return_value.filter.return_value.all.return_value = []
            
            # Mock scheduler status
            with patch('src.api.realtime.get_enhanced_scheduler') as mock_get_scheduler:
                mock_scheduler = Mock()
                mock_scheduler.get_enhanced_schedule_status.return_value = {"status": "running"}
                mock_get_scheduler.return_value = mock_scheduler
                
                result = await self.manager.get_current_monitoring_status()
                
                assert "timestamp" in result
                assert "active_runs" in result
                assert "recent_completed" in result
                assert "failed_runs" in result
                assert "statistics" in result
                assert "summary" in result
    
    @pytest.mark.asyncio
    async def test_get_system_health(self):
        """Test getting system health status."""
        with patch('src.api.realtime.get_db') as mock_get_db:
            mock_db = Mock()
            mock_get_db.return_value.__enter__.return_value = mock_db
            mock_db.execute.return_value = None
            
            with patch('src.api.realtime.get_monitoring_statistics') as mock_get_stats:
                mock_stats = Mock()
                mock_get_stats.return_value = mock_stats
                
                with patch('src.api.realtime.get_enhanced_scheduler') as mock_get_scheduler:
                    mock_scheduler = Mock()
                    mock_scheduler.running = True
                    mock_get_scheduler.return_value = mock_scheduler
                    
                    result = await self.manager.get_system_health()
                    
                    assert "overall_status" in result
                    assert "services" in result
                    assert "last_check" in result
                    assert result["services"]["database"]["status"] == "healthy"
                    assert result["services"]["scheduler"]["status"] == "healthy"


class TestWebSocketEndpoint:
    """Test the WebSocket endpoint."""
    
    @pytest.mark.asyncio
    async def test_websocket_endpoint_connection(self):
        """Test WebSocket endpoint connection."""
        mock_websocket = Mock(spec=WebSocket)
        mock_websocket.accept = AsyncMock()
        mock_websocket.receive_text = AsyncMock(side_effect=Exception("Test disconnect"))
        mock_websocket.send_text = AsyncMock()
        
        # Reset manager for clean test
        manager.active_connections.clear()
        manager.connection_metadata.clear()
        
        try:
            await websocket_endpoint(mock_websocket)
        except Exception:
            pass  # Expected due to our mock disconnect
        
        mock_websocket.accept.assert_called_once()
        mock_websocket.send_text.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_websocket_ping_pong(self):
        """Test WebSocket ping/pong functionality."""
        mock_websocket = Mock(spec=WebSocket)
        mock_websocket.accept = AsyncMock()
        mock_websocket.send_text = AsyncMock()
        
        # Simulate ping message
        mock_websocket.receive_text = AsyncMock(return_value=json.dumps({"type": "ping"}))
        
        # Reset manager for clean test
        manager.active_connections.clear()
        manager.connection_metadata.clear()
        
        # Start the endpoint but limit execution time
        try:
            await asyncio.wait_for(websocket_endpoint(mock_websocket), timeout=0.1)
        except asyncio.TimeoutError:
            pass  # Expected timeout
        
        # Verify pong was sent
        pong_calls = [call for call in mock_websocket.send_text.call_args_list 
                     if '"type": "pong"' in call[0][0]]
        assert len(pong_calls) > 0


class TestClientRequestHandling:
    """Test client request handling."""
    
    @pytest.mark.asyncio
    async def test_handle_client_request_statistics(self):
        """Test handling statistics request."""
        mock_websocket = Mock(spec=WebSocket)
        mock_websocket.send_text = AsyncMock()
        
        message = {"type": "request_update", "request_type": "statistics"}
        
        with patch('src.api.realtime.get_monitoring_statistics') as mock_get_stats:
            mock_stats = Mock()
            mock_stats.get_comprehensive_statistics = AsyncMock(return_value={"test": "data"})
            mock_get_stats.return_value = mock_stats
            
            await handle_client_request(mock_websocket, message)
            
            mock_websocket.send_text.assert_called_once()
            sent_data = json.loads(mock_websocket.send_text.call_args[0][0])
            assert sent_data["type"] == "statistics_response"
            assert sent_data["data"] == {"test": "data"}
    
    @pytest.mark.asyncio
    async def test_handle_client_request_monitoring_status(self):
        """Test handling monitoring status request."""
        mock_websocket = Mock(spec=WebSocket)
        mock_websocket.send_text = AsyncMock()
        
        message = {"type": "request_update", "request_type": "monitoring_status"}
        
        with patch('src.api.realtime.get_db') as mock_get_db:
            mock_db = Mock()
            mock_get_db.return_value.__enter__.return_value = mock_db
            mock_db.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = []
            mock_db.query.return_value.filter.return_value.all.return_value = []
            
            with patch('src.api.realtime.get_enhanced_scheduler') as mock_get_scheduler:
                mock_scheduler = Mock()
                mock_scheduler.get_enhanced_schedule_status.return_value = {"status": "running"}
                mock_get_scheduler.return_value = mock_scheduler
                
                await handle_client_request(mock_websocket, message)
                
                mock_websocket.send_text.assert_called_once()
                sent_data = json.loads(mock_websocket.send_text.call_args[0][0])
                assert sent_data["type"] == "monitoring_status_response"
    
    @pytest.mark.asyncio
    async def test_handle_client_request_error(self):
        """Test handling client request with error."""
        mock_websocket = Mock(spec=WebSocket)
        mock_websocket.send_text = AsyncMock()
        
        message = {"type": "request_update", "request_type": "invalid_type"}
        
        await handle_client_request(mock_websocket, message)
        
        mock_websocket.send_text.assert_called_once()
        sent_data = json.loads(mock_websocket.send_text.call_args[0][0])
        assert sent_data["type"] == "error"


class TestRealtimeDataFunctions:
    """Test real-time data retrieval functions."""
    
    @pytest.mark.asyncio
    async def test_get_recent_changes_for_realtime(self):
        """Test getting recent changes for real-time updates."""
        with patch('src.api.realtime.get_db') as mock_get_db:
            mock_db = Mock()
            mock_get_db.return_value.__enter__.return_value = mock_db
            
            # Mock form change with relationships
            mock_change = Mock()
            mock_change.id = 1
            mock_change.form = Mock()
            mock_change.form.name = "Test Form"
            mock_change.agency = Mock()
            mock_change.agency.name = "Test Agency"
            mock_change.change_type = "content_update"
            mock_change.severity = "high"
            mock_change.status = "new"
            mock_change.detected_at = datetime.utcnow()
            mock_change.ai_confidence_score = 85
            mock_change.ai_change_category = "regulatory"
            
            mock_db.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = [mock_change]
            
            result = await get_recent_changes_for_realtime()
            
            assert len(result) == 1
            assert result[0]["id"] == 1
            assert result[0]["form_name"] == "Test Form"
            assert result[0]["agency_name"] == "Test Agency"
            assert result[0]["change_type"] == "content_update"
            assert result[0]["severity"] == "high"
    
    @pytest.mark.asyncio
    async def test_get_active_alerts_for_realtime(self):
        """Test getting active alerts for real-time updates."""
        with patch('src.api.realtime.get_db') as mock_get_db:
            mock_db = Mock()
            mock_get_db.return_value.__enter__.return_value = mock_db
            
            # Mock notification
            mock_alert = Mock()
            mock_alert.id = 1
            mock_alert.type = "critical"
            mock_alert.message = "Test alert"
            mock_alert.severity = "high"
            mock_alert.created_at = datetime.utcnow()
            mock_alert.is_read = False
            
            mock_db.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = [mock_alert]
            
            result = await get_active_alerts_for_realtime()
            
            assert len(result) == 1
            assert result[0]["id"] == 1
            assert result[0]["type"] == "critical"
            assert result[0]["message"] == "Test alert"
            assert result[0]["severity"] == "high"
            assert result[0]["is_read"] == False
    
    @pytest.mark.asyncio
    async def test_broadcast_monitoring_event(self):
        """Test broadcasting monitoring events."""
        with patch('src.api.realtime.manager') as mock_manager:
            mock_manager.broadcast = AsyncMock()
            
            event_data = {"test": "event_data"}
            await broadcast_monitoring_event("test_event", event_data)
            
            mock_manager.broadcast.assert_called_once()
            broadcasted_message = mock_manager.broadcast.call_args[0][0]
            assert broadcasted_message["type"] == "test_event"
            assert broadcasted_message["data"] == event_data


class TestRealtimeIntegration:
    """Integration tests for real-time functionality."""
    
    @pytest.mark.asyncio
    async def test_full_realtime_workflow(self):
        """Test complete real-time workflow."""
        # Create a new manager instance for testing
        test_manager = ConnectionManager()
        
        # Mock WebSocket
        mock_websocket = Mock(spec=WebSocket)
        mock_websocket.send_text = AsyncMock()
        mock_websocket.accept = AsyncMock()
        
        # Test connection
        await test_manager.connect(mock_websocket, "test_client")
        assert mock_websocket in test_manager.active_connections
        
        # Test initial data sending
        mock_websocket.send_text.assert_called_once()
        initial_data = json.loads(mock_websocket.send_text.call_args[0][0])
        assert initial_data["type"] == "initial_data"
        assert "statistics" in initial_data
        assert "monitoring_status" in initial_data
        assert "system_health" in initial_data
        
        # Test broadcasting
        test_message = {"type": "test_broadcast", "data": "test"}
        await test_manager.broadcast(test_message)
        
        # Verify broadcast was sent
        broadcast_calls = [call for call in mock_websocket.send_text.call_args_list 
                          if '"type": "test_broadcast"' in call[0][0]]
        assert len(broadcast_calls) > 0
        
        # Test disconnection
        test_manager.disconnect(mock_websocket)
        assert mock_websocket not in test_manager.active_connections


if __name__ == "__main__":
    pytest.main([__file__]) 