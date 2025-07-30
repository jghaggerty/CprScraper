from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict
import logging
from datetime import datetime, timedelta

from ..database.connection import get_db, init_db
from ..database.models import Agency, Form, FormChange, MonitoringRun, Notification
from ..scheduler.monitoring_scheduler import get_scheduler
from ..notifications.notifier import NotificationManager
from ..utils.config_loader import load_agency_config, get_all_forms

# Initialize logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize database
init_db()

# Create FastAPI app
app = FastAPI(
    title="Payroll Monitoring System",
    description="AI-powered monitoring system for government payroll reporting requirements",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Pydantic models for API requests/responses
class AgencyResponse(BaseModel):
    id: int
    name: str
    abbreviation: Optional[str]
    agency_type: str
    base_url: str
    is_active: bool
    
class FormResponse(BaseModel):
    id: int
    name: str
    title: str
    form_url: Optional[str]
    check_frequency: str
    is_active: bool
    last_checked: Optional[datetime]
    
class FormChangeResponse(BaseModel):
    id: int
    form_name: str
    agency_name: str
    change_type: str
    change_description: str
    severity: str
    status: str
    detected_at: datetime
    effective_date: Optional[datetime]
    
class MonitoringStats(BaseModel):
    total_agencies: int
    total_forms: int
    active_forms: int
    changes_last_24h: int
    changes_last_week: int
    last_monitoring_run: Optional[datetime]
    
class NotificationRequest(BaseModel):
    form_change_id: int
    channels: Optional[List[str]] = None


# API Endpoints

@app.get("/")
async def dashboard():
    """Serve the main dashboard page."""
    return HTMLResponse(content="""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Payroll Monitoring Dashboard</title>
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }
            .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 10px; margin-bottom: 20px; }
            .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-bottom: 20px; }
            .stat-card { background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
            .stat-number { font-size: 2em; font-weight: bold; color: #667eea; }
            .stat-label { color: #666; margin-top: 5px; }
            .content-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
            .panel { background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
            .change-item { border-bottom: 1px solid #eee; padding: 10px 0; }
            .severity-high { border-left: 4px solid #dc3545; padding-left: 10px; }
            .severity-medium { border-left: 4px solid #ffc107; padding-left: 10px; }
            .severity-low { border-left: 4px solid #28a745; padding-left: 10px; }
            .btn { background: #667eea; color: white; padding: 10px 20px; border: none; border-radius: 5px; cursor: pointer; }
            .btn:hover { background: #5a6fd8; }
        </style>
    </head>
    <body>
        <div class="header">
            <h1>🚨 Payroll Monitoring Dashboard</h1>
            <p>Monitoring certified payroll reporting requirements across all 50 states and federal agencies</p>
        </div>
        
        <div class="stats-grid" id="stats-grid">
            <!-- Stats will be loaded here -->
        </div>
        
        <div class="content-grid">
            <div class="panel">
                <h3>📊 Recent Changes</h3>
                <div id="recent-changes">
                    <!-- Recent changes will be loaded here -->
                </div>
            </div>
            
            <div class="panel">
                <h3>⚙️ System Status</h3>
                <div id="system-status">
                    <!-- System status will be loaded here -->
                </div>
                <button class="btn" onclick="runImmediateCheck()">Run Immediate Check</button>
            </div>
        </div>
        
        <div class="panel" style="margin-top: 20px;">
            <h3>📈 Monitoring Activity</h3>
            <canvas id="activityChart" width="400" height="200"></canvas>
        </div>
        
        <script>
            // Load dashboard data
            async function loadDashboard() {
                try {
                    // Load stats
                    const statsResponse = await fetch('/api/stats');
                    const stats = await statsResponse.json();
                    displayStats(stats);
                    
                    // Load recent changes
                    const changesResponse = await fetch('/api/changes?limit=10');
                    const changes = await changesResponse.json();
                    displayRecentChanges(changes);
                    
                    // Load system status
                    const statusResponse = await fetch('/api/scheduler/status');
                    const status = await statusResponse.json();
                    displaySystemStatus(status);
                    
                    // Load activity chart
                    loadActivityChart();
                    
                } catch (error) {
                    console.error('Error loading dashboard:', error);
                }
            }
            
            function displayStats(stats) {
                const statsGrid = document.getElementById('stats-grid');
                statsGrid.innerHTML = `
                    <div class="stat-card">
                        <div class="stat-number">${stats.total_agencies}</div>
                        <div class="stat-label">Total Agencies</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number">${stats.total_forms}</div>
                        <div class="stat-label">Total Forms</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number">${stats.active_forms}</div>
                        <div class="stat-label">Active Forms</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number">${stats.changes_last_24h}</div>
                        <div class="stat-label">Changes (24h)</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number">${stats.changes_last_week}</div>
                        <div class="stat-label">Changes (Week)</div>
                    </div>
                `;
            }
            
            function displayRecentChanges(changes) {
                const container = document.getElementById('recent-changes');
                if (changes.length === 0) {
                    container.innerHTML = '<p>No recent changes detected.</p>';
                    return;
                }
                
                const changesHtml = changes.map(change => `
                    <div class="change-item severity-${change.severity}">
                        <strong>${change.agency_name} - ${change.form_name}</strong><br>
                        <small>${change.change_description}</small><br>
                        <small>Detected: ${new Date(change.detected_at).toLocaleString()}</small>
                    </div>
                `).join('');
                
                container.innerHTML = changesHtml;
            }
            
            function displaySystemStatus(status) {
                const container = document.getElementById('system-status');
                const statusText = status.running ? '🟢 Running' : '🔴 Stopped';
                container.innerHTML = `
                    <p><strong>Scheduler:</strong> ${statusText}</p>
                    <p><strong>Scheduled Jobs:</strong> ${status.scheduled_jobs}</p>
                    <p><strong>Next Run:</strong> ${status.next_run ? new Date(status.next_run).toLocaleString() : 'N/A'}</p>
                `;
            }
            
            async function loadActivityChart() {
                try {
                    const response = await fetch('/api/activity-stats');
                    const data = await response.json();
                    
                    const ctx = document.getElementById('activityChart').getContext('2d');
                    new Chart(ctx, {
                        type: 'line',
                        data: {
                            labels: data.dates,
                            datasets: [{
                                label: 'Monitoring Runs',
                                data: data.monitoring_runs,
                                borderColor: '#667eea',
                                backgroundColor: 'rgba(102, 126, 234, 0.1)',
                                tension: 0.1
                            }, {
                                label: 'Changes Detected',
                                data: data.changes_detected,
                                borderColor: '#f093fb',
                                backgroundColor: 'rgba(240, 147, 251, 0.1)',
                                tension: 0.1
                            }]
                        },
                        options: {
                            responsive: true,
                            scales: {
                                y: {
                                    beginAtZero: true
                                }
                            }
                        }
                    });
                } catch (error) {
                    console.error('Error loading activity chart:', error);
                }
            }
            
            async function runImmediateCheck() {
                try {
                    const response = await fetch('/api/scheduler/run-immediate', { method: 'POST' });
                    if (response.ok) {
                        alert('Immediate monitoring check started!');
                        setTimeout(loadDashboard, 2000); // Reload after 2 seconds
                    } else {
                        alert('Failed to start immediate check');
                    }
                } catch (error) {
                    console.error('Error running immediate check:', error);
                    alert('Error starting immediate check');
                }
            }
            
            // Auto-refresh dashboard every 5 minutes
            setInterval(loadDashboard, 5 * 60 * 1000);
            
            // Load dashboard on page load
            loadDashboard();
        </script>
    </body>
    </html>
    """)

@app.get("/api/stats", response_model=MonitoringStats)
async def get_monitoring_stats():
    """Get overall monitoring statistics."""
    with get_db() as db:
        total_agencies = db.query(Agency).count()
        total_forms = db.query(Form).count()
        active_forms = db.query(Form).filter(Form.is_active == True).count()
        
        # Changes in last 24 hours
        yesterday = datetime.utcnow() - timedelta(days=1)
        changes_24h = db.query(FormChange).filter(
            FormChange.detected_at >= yesterday
        ).count()
        
        # Changes in last week
        week_ago = datetime.utcnow() - timedelta(days=7)
        changes_week = db.query(FormChange).filter(
            FormChange.detected_at >= week_ago
        ).count()
        
        # Last monitoring run
        last_run = db.query(MonitoringRun).order_by(
            MonitoringRun.started_at.desc()
        ).first()
        
        return MonitoringStats(
            total_agencies=total_agencies,
            total_forms=total_forms,
            active_forms=active_forms,
            changes_last_24h=changes_24h,
            changes_last_week=changes_week,
            last_monitoring_run=last_run.started_at if last_run else None
        )

@app.get("/api/agencies", response_model=List[AgencyResponse])
async def get_agencies():
    """Get all agencies."""
    with get_db() as db:
        agencies = db.query(Agency).all()
        return [
            AgencyResponse(
                id=agency.id,
                name=agency.name,
                abbreviation=agency.abbreviation,
                agency_type=agency.agency_type,
                base_url=agency.base_url,
                is_active=agency.is_active
            )
            for agency in agencies
        ]

@app.get("/api/agencies/{agency_id}/forms", response_model=List[FormResponse])
async def get_agency_forms(agency_id: int):
    """Get forms for a specific agency."""
    with get_db() as db:
        agency = db.query(Agency).filter(Agency.id == agency_id).first()
        if not agency:
            raise HTTPException(status_code=404, detail="Agency not found")
        
        return [
            FormResponse(
                id=form.id,
                name=form.name,
                title=form.title,
                form_url=form.form_url,
                check_frequency=form.check_frequency,
                is_active=form.is_active,
                last_checked=form.last_checked
            )
            for form in agency.forms
        ]

@app.get("/api/changes", response_model=List[FormChangeResponse])
async def get_form_changes(
    limit: int = 50,
    agency_id: Optional[int] = None,
    severity: Optional[str] = None
):
    """Get form changes with optional filtering."""
    with get_db() as db:
        query = db.query(FormChange).join(Form).join(Agency)
        
        if agency_id:
            query = query.filter(Agency.id == agency_id)
        
        if severity:
            query = query.filter(FormChange.severity == severity)
        
        changes = query.order_by(FormChange.detected_at.desc()).limit(limit).all()
        
        return [
            FormChangeResponse(
                id=change.id,
                form_name=change.form.name,
                agency_name=change.form.agency.name,
                change_type=change.change_type,
                change_description=change.change_description,
                severity=change.severity,
                status=change.status,
                detected_at=change.detected_at,
                effective_date=change.effective_date
            )
            for change in changes
        ]

@app.get("/api/activity-stats")
async def get_activity_stats():
    """Get activity statistics for charts."""
    with get_db() as db:
        # Get data for the last 30 days
        dates = []
        monitoring_runs = []
        changes_detected = []
        
        for i in range(29, -1, -1):
            date = datetime.utcnow().date() - timedelta(days=i)
            dates.append(date.strftime('%Y-%m-%d'))
            
            # Count monitoring runs for this date
            runs = db.query(MonitoringRun).filter(
                MonitoringRun.started_at >= datetime.combine(date, datetime.min.time()),
                MonitoringRun.started_at < datetime.combine(date + timedelta(days=1), datetime.min.time())
            ).count()
            monitoring_runs.append(runs)
            
            # Count changes detected for this date
            changes = db.query(FormChange).filter(
                FormChange.detected_at >= datetime.combine(date, datetime.min.time()),
                FormChange.detected_at < datetime.combine(date + timedelta(days=1), datetime.min.time())
            ).count()
            changes_detected.append(changes)
        
        return {
            "dates": dates,
            "monitoring_runs": monitoring_runs,
            "changes_detected": changes_detected
        }

@app.get("/api/scheduler/status")
async def get_scheduler_status():
    """Get scheduler status."""
    scheduler = get_scheduler()
    return scheduler.get_schedule_status()

@app.post("/api/scheduler/start")
async def start_scheduler():
    """Start the monitoring scheduler."""
    try:
        scheduler = get_scheduler()
        scheduler.start()
        return {"message": "Scheduler started successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/scheduler/stop")
async def stop_scheduler():
    """Stop the monitoring scheduler."""
    try:
        scheduler = get_scheduler()
        scheduler.stop()
        return {"message": "Scheduler stopped successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/scheduler/run-immediate")
async def run_immediate_monitoring(background_tasks: BackgroundTasks):
    """Run immediate monitoring check."""
    def run_check():
        scheduler = get_scheduler()
        scheduler.run_immediate_check()
    
    background_tasks.add_task(run_check)
    return {"message": "Immediate monitoring check started"}

@app.post("/api/notifications/send")
async def send_notification(request: NotificationRequest):
    """Send notification for a form change."""
    try:
        notification_manager = NotificationManager()
        results = await notification_manager.send_change_notification(request.form_change_id)
        return {"message": "Notifications sent", "results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/notifications/test")
async def test_notifications():
    """Test all notification channels."""
    try:
        notification_manager = NotificationManager()
        results = await notification_manager.test_notifications()
        return {"message": "Test notifications sent", "results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "timestamp": datetime.utcnow()}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)