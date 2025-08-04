"""
Real-time WebSocket API for Compliance Monitoring Dashboard

Provides WebSocket endpoints for real-time updates including:
- Monitoring run status
- Live statistics updates
- Real-time alerts and notifications
- System health status
- Change detection events
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Set
from fastapi import WebSocket, WebSocketDisconnect, APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import and_, func

from ..database.connection import get_db
from ..database.models import Agency, Form, FormChange, MonitoringRun, Notification
from ..monitors.monitoring_statistics import get_monitoring_statistics, MonitoringStatistics
from ..scheduler.enhanced_scheduler import get_enhanced_scheduler

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/realtime", tags=["realtime"])

class ConnectionManager:
    """Manages WebSocket connections and broadcasts real-time updates."""
    
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
        self.connection_metadata: Dict[WebSocket, Dict[str, Any]] = {}
        self.broadcast_queue = asyncio.Queue()
        self.stats = get_monitoring_statistics()
        self.scheduler = get_enhanced_scheduler()
        
    async def connect(self, websocket: WebSocket, client_type: str = "dashboard"):
        """Accept a new WebSocket connection."""
        await websocket.accept()
        self.active_connections.add(websocket)
        self.connection_metadata[websocket] = {
            "client_type": client_type,
            "connected_at": datetime.utcnow(),
            "last_activity": datetime.utcnow()
        }
        logger.info(f"WebSocket connected: {client_type} (total: {len(self.active_connections)})")
        
        # Send initial data
        await self.send_initial_data(websocket)
    
    def disconnect(self, websocket: WebSocket):
        """Remove a WebSocket connection."""
        self.active_connections.discard(websocket)
        if websocket in self.connection_metadata:
            del self.connection_metadata[websocket]
        logger.info(f"WebSocket disconnected (total: {len(self.active_connections)})")
    
    async def send_initial_data(self, websocket: WebSocket):
        """Send initial data to a new connection."""
        try:
            # Get current statistics
            stats = await self.stats.get_comprehensive_statistics()
            
            # Get current monitoring status
            monitoring_status = await self.get_current_monitoring_status()
            
            # Send initial data
            initial_data = {
                "type": "initial_data",
                "timestamp": datetime.utcnow().isoformat(),
                "statistics": stats,
                "monitoring_status": monitoring_status,
                "system_health": await self.get_system_health()
            }
            
            await websocket.send_text(json.dumps(initial_data))
            
        except Exception as e:
            logger.error(f"Error sending initial data: {e}")
    
    async def broadcast(self, message: Dict[str, Any]):
        """Broadcast a message to all connected clients."""
        if not self.active_connections:
            return
        
        message_json = json.dumps(message)
        disconnected = set()
        
        for connection in self.active_connections:
            try:
                await connection.send_text(message_json)
                self.connection_metadata[connection]["last_activity"] = datetime.utcnow()
            except Exception as e:
                logger.error(f"Error broadcasting to connection: {e}")
                disconnected.add(connection)
        
        # Clean up disconnected connections
        for connection in disconnected:
            self.disconnect(connection)
    
    async def broadcast_statistics_update(self):
        """Broadcast updated statistics to all clients."""
        try:
            stats = await self.stats.get_comprehensive_statistics()
            await self.broadcast({
                "type": "statistics_update",
                "timestamp": datetime.utcnow().isoformat(),
                "data": stats
            })
        except Exception as e:
            logger.error(f"Error broadcasting statistics update: {e}")
    
    async def broadcast_monitoring_status(self, status: Dict[str, Any]):
        """Broadcast monitoring status update."""
        await self.broadcast({
            "type": "monitoring_status",
            "timestamp": datetime.utcnow().isoformat(),
            "data": status
        })
    
    async def broadcast_change_detected(self, change: Dict[str, Any]):
        """Broadcast when a new change is detected."""
        await self.broadcast({
            "type": "change_detected",
            "timestamp": datetime.utcnow().isoformat(),
            "data": change
        })
    
    async def broadcast_alert(self, alert: Dict[str, Any]):
        """Broadcast a new alert."""
        await self.broadcast({
            "type": "alert",
            "timestamp": datetime.utcnow().isoformat(),
            "data": alert
        })
    
    async def broadcast_system_health(self, health: Dict[str, Any]):
        """Broadcast system health update."""
        await self.broadcast({
            "type": "system_health",
            "timestamp": datetime.utcnow().isoformat(),
            "data": health
        })
    
    async def get_current_monitoring_status(self) -> Dict[str, Any]:
        """Get current monitoring run status."""
        try:
            with get_db() as db:
                # Get recent monitoring runs
                recent_runs = db.query(MonitoringRun).filter(
                    MonitoringRun.created_at >= datetime.utcnow() - timedelta(hours=24)
                ).order_by(MonitoringRun.created_at.desc()).limit(10).all()
                
                # Get active runs
                active_runs = db.query(MonitoringRun).filter(
                    MonitoringRun.status.in_(["running", "pending"])
                ).all()
                
                # Get scheduler status
                scheduler_status = self.scheduler.get_enhanced_schedule_status()
                
                return {
                    "recent_runs": [
                        {
                            "id": run.id,
                            "agency_id": run.agency_id,
                            "form_id": run.form_id,
                            "status": run.status,
                            "started_at": run.started_at.isoformat() if run.started_at else None,
                            "completed_at": run.completed_at.isoformat() if run.completed_at else None,
                            "changes_detected": run.changes_detected,
                            "error_message": run.error_message
                        }
                        for run in recent_runs
                    ],
                    "active_runs": len(active_runs),
                    "scheduler_status": scheduler_status,
                    "last_update": datetime.utcnow().isoformat()
                }
        except Exception as e:
            logger.error(f"Error getting monitoring status: {e}")
            return {"error": str(e)}
    
    async def get_system_health(self) -> Dict[str, Any]:
        """Get current system health status."""
        try:
            # Get basic system metrics
            health = {
                "overall_status": "healthy",
                "services": {},
                "last_check": datetime.utcnow().isoformat()
            }
            
            # Check database connection
            try:
                with get_db() as db:
                    db.execute("SELECT 1")
                    health["services"]["database"] = {"status": "healthy", "response_time": "fast"}
            except Exception as e:
                health["services"]["database"] = {"status": "unhealthy", "error": str(e)}
                health["overall_status"] = "degraded"
            
            # Check monitoring statistics
            try:
                stats = get_monitoring_statistics()
                health["services"]["monitoring_stats"] = {"status": "healthy"}
            except Exception as e:
                health["services"]["monitoring_stats"] = {"status": "unhealthy", "error": str(e)}
                health["overall_status"] = "degraded"
            
            # Check scheduler
            try:
                scheduler = get_enhanced_scheduler()
                if scheduler.running:
                    health["services"]["scheduler"] = {"status": "healthy", "running": True}
                else:
                    health["services"]["scheduler"] = {"status": "stopped", "running": False}
                    health["overall_status"] = "degraded"
            except Exception as e:
                health["services"]["scheduler"] = {"status": "unhealthy", "error": str(e)}
                health["overall_status"] = "degraded"
            
            return health
            
        except Exception as e:
            logger.error(f"Error getting system health: {e}")
            return {"overall_status": "unknown", "error": str(e)}

# Global connection manager
manager = ConnectionManager()

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates."""
    await manager.connect(websocket)
    
    try:
        while True:
            # Keep connection alive and handle client messages
            data = await websocket.receive_text()
            message = json.loads(data)
            
            # Update last activity
            if websocket in manager.connection_metadata:
                manager.connection_metadata[websocket]["last_activity"] = datetime.utcnow()
            
            # Handle client requests
            if message.get("type") == "request_update":
                await handle_client_request(websocket, message)
            elif message.get("type") == "ping":
                await websocket.send_text(json.dumps({"type": "pong", "timestamp": datetime.utcnow().isoformat()}))
                
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)

async def handle_client_request(websocket: WebSocket, message: Dict[str, Any]):
    """Handle client requests for specific data updates."""
    try:
        request_type = message.get("request_type")
        
        if request_type == "statistics":
            stats = await manager.stats.get_comprehensive_statistics()
            await websocket.send_text(json.dumps({
                "type": "statistics_response",
                "timestamp": datetime.utcnow().isoformat(),
                "data": stats
            }))
        
        elif request_type == "monitoring_status":
            status = await manager.get_current_monitoring_status()
            await websocket.send_text(json.dumps({
                "type": "monitoring_status_response",
                "timestamp": datetime.utcnow().isoformat(),
                "data": status
            }))
        
        elif request_type == "system_health":
            health = await manager.get_system_health()
            await websocket.send_text(json.dumps({
                "type": "system_health_response",
                "timestamp": datetime.utcnow().isoformat(),
                "data": health
            }))
        
        elif request_type == "recent_changes":
            changes = await get_recent_changes_for_realtime()
            await websocket.send_text(json.dumps({
                "type": "recent_changes_response",
                "timestamp": datetime.utcnow().isoformat(),
                "data": changes
            }))
        
        elif request_type == "active_alerts":
            alerts = await get_active_alerts_for_realtime()
            await websocket.send_text(json.dumps({
                "type": "active_alerts_response",
                "timestamp": datetime.utcnow().isoformat(),
                "data": alerts
            }))
            
    except Exception as e:
        logger.error(f"Error handling client request: {e}")
        await websocket.send_text(json.dumps({
            "type": "error",
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e)
        }))

async def get_recent_changes_for_realtime() -> List[Dict[str, Any]]:
    """Get recent changes for real-time updates."""
    try:
        with get_db() as db:
            recent_changes = db.query(FormChange).filter(
                FormChange.detected_at >= datetime.utcnow() - timedelta(hours=24)
            ).order_by(FormChange.detected_at.desc()).limit(20).all()
            
            return [
                {
                    "id": change.id,
                    "form_name": change.form.name if change.form else "Unknown",
                    "agency_name": change.agency.name if change.agency else "Unknown",
                    "change_type": change.change_type,
                    "severity": change.severity,
                    "status": change.status,
                    "detected_at": change.detected_at.isoformat(),
                    "ai_confidence_score": change.ai_confidence_score,
                    "ai_change_category": change.ai_change_category
                }
                for change in recent_changes
            ]
    except Exception as e:
        logger.error(f"Error getting recent changes: {e}")
        return []

async def get_active_alerts_for_realtime() -> List[Dict[str, Any]]:
    """Get active alerts for real-time updates."""
    try:
        with get_db() as db:
            active_alerts = db.query(Notification).filter(
                and_(
                    Notification.is_active == True,
                    Notification.created_at >= datetime.utcnow() - timedelta(days=7)
                )
            ).order_by(Notification.created_at.desc()).limit(10).all()
            
            return [
                {
                    "id": alert.id,
                    "type": alert.type,
                    "message": alert.message,
                    "severity": alert.severity,
                    "created_at": alert.created_at.isoformat(),
                    "is_read": alert.is_read
                }
                for alert in active_alerts
            ]
    except Exception as e:
        logger.error(f"Error getting active alerts: {e}")
        return []

# Background task for periodic updates
async def broadcast_periodic_updates():
    """Background task to broadcast periodic updates."""
    while True:
        try:
            # Broadcast statistics update every 30 seconds
            await manager.broadcast_statistics_update()
            
            # Broadcast system health every 60 seconds
            health = await manager.get_system_health()
            await manager.broadcast_system_health(health)
            
            # Wait before next update
            await asyncio.sleep(30)
            
        except Exception as e:
            logger.error(f"Error in periodic updates: {e}")
            await asyncio.sleep(60)  # Wait longer on error

# Start background task when module is imported
async def start_background_tasks():
    """Start background tasks for real-time updates."""
    asyncio.create_task(broadcast_periodic_updates())

# Export functions for external use
def get_connection_manager() -> ConnectionManager:
    """Get the global connection manager instance."""
    return manager

async def broadcast_monitoring_event(event_type: str, data: Dict[str, Any]):
    """Broadcast a monitoring event to all connected clients."""
    await manager.broadcast({
        "type": event_type,
        "timestamp": datetime.utcnow().isoformat(),
        "data": data
    }) 