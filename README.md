# 🚨 Payroll Monitoring System

An AI-powered monitoring system for government certified payroll reporting requirements across all 50 states, federal, and other government agencies. This system continuously monitors for changes in payroll forms, templates, and requirements, providing immediate alerts and comprehensive impact analysis.

## 🎯 Project Goals

**Goal 1:** Increased confidence in report maintenance  
**Goal 2:** Decreased report change requests  
**Objective:** Consistent, transparent, and proactive report updates

## 🏗️ System Architecture

The system consists of several integrated components:

- **Web Scraping Engine**: Monitors government websites for form changes
- **Change Detection**: AI-powered algorithms to identify modifications
- **Notification System**: Multi-channel alerts (Email, Slack, Teams)
- **Impact Analysis**: Comprehensive reporting on client and development impact
- **Automated Scheduler**: Regular monitoring with configurable frequencies
- **Web Dashboard**: Real-time monitoring and management interface
- **Database**: SQLite/PostgreSQL for data persistence

## 📋 Features

### Monitoring Capabilities
- ✅ All 50 US states monitoring
- ✅ Federal agencies (DOL, etc.)
- ✅ Form change detection (WH-347, CA_A1131, etc.)
- ✅ Automated scheduling (daily, weekly, monthly)
- ✅ Real-time change alerts

### Impact Analysis
- ✅ Client impact assessment
- ✅ Development effort estimation  
- ✅ Risk assessment and mitigation
- ✅ Timeline projections
- ✅ Resource planning

### Notifications
- ✅ Email notifications with detailed HTML reports
- ✅ Slack integration with rich formatting
- ✅ Microsoft Teams webhook support
- ✅ Customizable notification templates

### Dashboard & Reporting
- ✅ Real-time web dashboard
- ✅ Activity monitoring and statistics
- ✅ Change history tracking
- ✅ Executive summary reports
- ✅ API endpoints for integration

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- Dependencies (installed via requirements.txt)
- Optional: Chrome/Chromium for JavaScript-heavy sites

### Installation

1. **Clone the repository**
```bash
git clone <repository-url>
cd payroll-monitoring-system
```

2. **Install dependencies**
```bash
pip install -r requirements.txt
```

3. **Create required directories**
```bash
mkdir -p data logs static templates
```

4. **Initialize the system**
```bash
python main.py init-db
python main.py load-data
```

5. **Start the system**
```bash
python main.py start
```

The dashboard will be available at http://localhost:8000

### Alternative Commands

```bash
# Initialize database only
python main.py init-db

# Load agency configuration
python main.py load-data

# Run immediate monitoring check
python main.py monitor

# Start only the dashboard
python main.py dashboard

# Start only the scheduler
python main.py scheduler

# Run system tests
python main.py test
```

## ⚙️ Configuration

### Environment Variables

Create a `.env` file with the following variables:

```env
# Database
DATABASE_URL=sqlite:///./data/payroll_monitor.db
DB_ECHO=false

# Email Notifications
SMTP_SERVER=smtp.gmail.com
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
FROM_EMAIL=your-email@gmail.com
ALERT_EMAIL_1=stakeholder1@company.com
ALERT_EMAIL_2=stakeholder2@company.com

# Slack (optional)
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...

# Teams (optional)
TEAMS_WEBHOOK_URL=https://company.webhook.office.com/...
```

### Agency Configuration

The system uses `config/agencies.yaml` to define which agencies and forms to monitor. The configuration includes:

- Federal agencies (Department of Labor, etc.)
- All 50 state agencies
- Form details (URLs, check frequencies, contact information)
- Monitoring settings
- Notification preferences

Example configuration structure:
```yaml
federal:
  department_of_labor:
    name: "U.S. Department of Labor"
    base_url: "https://www.dol.gov"
    forms:
      - name: "WH-347"
        title: "Statement of Compliance for Federal and Federally Assisted Construction Projects"
        url: "https://www.dol.gov/sites/dolgov/files/WHD/legacy/files/wh347.pdf"
        check_frequency: "daily"

states:
  california:
    name: "California Department of Industrial Relations"
    abbreviation: "CA"
    forms:
      - name: "A1-131"
        title: "California Certified Payroll Report"
        check_frequency: "daily"
```

## 📊 Dashboard Features

The web dashboard provides:

### Overview Statistics
- Total agencies and forms monitored
- Recent changes (24h, weekly)
- System status and health

### Recent Changes
- Real-time change notifications
- Severity indicators (low, medium, high, critical)
- Agency and form details

### System Controls
- Start/stop scheduler
- Run immediate monitoring checks
- Test notification systems

### Activity Charts
- Monitoring run history
- Change detection trends
- Performance metrics

## 🔄 Development Workflow

When a change is detected, the system follows this workflow:

### 1. **Change Detection & Notification**
- System detects form modification
- Immediate notification sent to stakeholders
- Change details logged in database

### 2. **Impact Assessment**
Information provided includes:
- Agency and report details
- Detailed description of changes
- Resource links (specifications, instructions, agency contact)
- Field mapping information (current vs. updated)
- Date changes take effect
- Clients impacted (number and ICP segment percentage)

### 3. **Development Process**
Following strict guidelines:
- **Evaluation**: Effort, risk, and impact assessment
- **Development**: Implementation following report update guidelines
- **QA**: Comprehensive testing including weekly/bi-weekly scenarios
- **EUT**: End-user testing and final review
- **Production**: Release with stakeholder notification
- **Monitoring**: 3-month feedback collection period

### 4. **Quality Assurance**
Testing includes:
- Weekly/Bi-weekly reporting scenarios
- Time entries and data entry validation
- ST/OT/Other hours calculations
- Old and new fringes handling
- Report options and no work reporting
- Calculation evaluation and font/alignment checks

## 🔧 API Endpoints

The system provides REST API endpoints:

### Monitoring
- `GET /api/stats` - Overall monitoring statistics
- `GET /api/agencies` - List all agencies
- `GET /api/agencies/{id}/forms` - Forms for specific agency
- `GET /api/changes` - Recent form changes

### Scheduler Control
- `GET /api/scheduler/status` - Scheduler status
- `POST /api/scheduler/start` - Start scheduler
- `POST /api/scheduler/stop` - Stop scheduler
- `POST /api/scheduler/run-immediate` - Run immediate check

### Notifications
- `POST /api/notifications/send` - Send notification for specific change
- `POST /api/notifications/test` - Test all notification channels

### Health Check
- `GET /health` - System health status

## 🏢 Production Deployment

### Docker Deployment

1. **Create Dockerfile**
```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
RUN python main.py init-db

EXPOSE 8000
CMD ["python", "main.py", "start"]
```

2. **Build and run**
```bash
docker build -t payroll-monitor .
docker run -p 8000:8000 payroll-monitor
```

### Environment Setup

For production:
- Use PostgreSQL instead of SQLite
- Configure proper SMTP server
- Set up SSL/TLS for web dashboard
- Configure reverse proxy (nginx)
- Set up monitoring and logging
- Configure backup procedures

## 📈 Monitoring & Maintenance

### System Health
- Dashboard shows real-time system status
- Automated health checks
- Error logging and alerting

### Database Maintenance
- Automatic cleanup of old monitoring runs (90 days)
- Notification history cleanup (180 days)
- Regular database backups

### Performance Monitoring
- Monitoring run performance tracking
- Response time metrics
- Error rate monitoring

## 🔒 Security Considerations

- Secure storage of credentials using environment variables
- HTTPS for all external communications
- Rate limiting for web scraping
- Input validation and sanitization
- Audit logging for all changes

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 📞 Support

For questions or support:
- Check the logs in the `logs/` directory
- Use the test command: `python main.py test`
- Review the configuration in `config/agencies.yaml`
- Check the dashboard at http://localhost:8000

## 🗺️ Roadmap

### Phase 1 (Current)
- ✅ Core monitoring system
- ✅ Basic notification system
- ✅ Web dashboard
- ✅ Impact analysis

### Phase 2 (Planned)
- [ ] Machine learning for change prediction
- [ ] Advanced form parsing and comparison
- [ ] Integration with project management tools
- [ ] Mobile notifications
- [ ] Advanced analytics and reporting

### Phase 3 (Future)
- [ ] Multi-language support
- [ ] Custom notification rules
- [ ] Integration with CPR system
- [ ] Automated testing framework
- [ ] Advanced AI-powered insights

---

**Built with ❤️ for efficient payroll compliance management**