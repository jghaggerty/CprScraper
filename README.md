# Payroll Monitoring System

An AI-powered monitoring system that tracks government agency form changes across all 50 states and federal agencies for certified payroll reporting requirements.

## Features

- **Comprehensive Monitoring**: Tracks forms from all 50 states and federal agencies
- **AI-Powered Analysis**: Uses machine learning to detect meaningful changes
- **Real-time Notifications**: Email, Slack, and Teams integration
- **Web Dashboard**: Real-time monitoring dashboard with charts and statistics
- **Automated Scheduling**: Configurable monitoring frequencies
- **Change Detection**: Sophisticated content comparison and change tracking
- **Database Storage**: Persistent storage of all monitoring data
- **API Access**: RESTful API for integration with other systems

## Quick Start

### Prerequisites

- Python 3.11+
- Chrome/Chromium browser (for Selenium web scraping)
- SMTP server for email notifications

### Installation

1. **Clone the repository**

   ```bash
   git clone <repository-url>
   cd CprScraper
   ```

2. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables**

   ```bash
   cp env.example .env
   # Edit .env with your configuration
   ```

4. **Initialize the database**

   ```bash
   python main.py init-db
   ```

5. **Load agency data**

   ```bash
   python main.py load-data
   ```

6. **Start the system**

   ```bash
   python main.py start
   ```

## Configuration

### Environment Variables

Create a `.env` file with the following variables:

```bash
# Required
SMTP_SERVER=smtp.gmail.com
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
FROM_EMAIL=alerts@yourcompany.com
ALERT_EMAIL_1=admin@yourcompany.com

# Optional
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK
TEAMS_WEBHOOK_URL=https://yourcompany.webhook.office.com/webhookb2/YOUR/WEBHOOK
OPENAI_API_KEY=your-openai-api-key
```

### Agency Configuration

Edit `config/agencies.yaml` to add or modify agencies and forms:

```yaml
federal:
  department_of_labor:
    name: "U.S. Department of Labor"
    base_url: "https://www.dol.gov"
    forms:
      - name: "WH-347"
        title: "Statement of Compliance for Federal and Federally Assisted Construction Projects"
        url: "https://www.dol.gov/agencies/whd/government-contracts/construction"
        check_frequency: "daily"
```

## Usage

### Command Line Interface

```bash
# Initialize database
python main.py init-db

# Load agency data from configuration
python main.py load-data

# Run immediate monitoring check
python main.py monitor

# Run system tests
python main.py test

# Start web dashboard only
python main.py dashboard

# Start scheduler only
python main.py scheduler

# Start full system (scheduler + dashboard)
python main.py start
```

### Web Dashboard

Access the web dashboard at `http://localhost:8000` to view:

- Real-time monitoring statistics
- Recent form changes
- System status
- Activity charts
- Agency and form management

### API Endpoints

The system provides RESTful API endpoints:

- `GET /api/stats` - Get monitoring statistics
- `GET /api/agencies` - List all agencies
- `GET /api/changes` - Get form changes
- `POST /api/scheduler/run-immediate` - Run immediate monitoring
- `GET /health` - Health check

## Docker Deployment

### Using Docker Compose

1. **Build and start services**

   ```bash
   docker-compose up -d
   ```

2. **View logs**

   ```bash
   docker-compose logs -f app
   ```

3. **Stop services**

   ```bash
   docker-compose down
   ```

### Using Docker

1. **Build image**

   ```bash
   docker build -t payroll-monitor .
   ```

2. **Run container**

   ```bash
   docker run -p 8000:8000 --env-file .env payroll-monitor
   ```

## Architecture

### Components

- **Web Scraper**: Monitors government websites for changes
- **AI Analysis**: Analyzes content changes using machine learning
- **Scheduler**: Manages automated monitoring schedules
- **Notification System**: Sends alerts via multiple channels
- **Database**: Stores monitoring data and change history
- **API**: Provides RESTful interface for external systems
- **Dashboard**: Web interface for monitoring and management

### Data Flow

1. **Scheduler** triggers monitoring jobs based on configuration
2. **Web Scraper** fetches content from government websites
3. **AI Analysis** compares content and detects meaningful changes
4. **Database** stores monitoring results and change history
5. **Notification System** sends alerts for detected changes
6. **Dashboard** displays real-time statistics and data

## Development

### Project Structure

```plaintext
CprScraper/
├── config/
│   └── agencies.yaml          # Agency and form configurations
├── src/
│   ├── analysis/              # AI analysis components
│   ├── api/                   # FastAPI web interface
│   ├── database/              # Database models and connection
│   ├── monitors/              # Web scraping and monitoring
│   ├── notifications/         # Notification system
│   ├── scheduler/             # Task scheduling
│   └── utils/                 # Utility functions
├── tests/                     # Test files
├── main.py                    # Main application entry point
├── requirements.txt           # Python dependencies
└── docker-compose.yml         # Docker deployment
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src

# Run specific test file
pytest tests/test_analysis.py
```

### Code Quality

```bash
# Format code
black src/ tests/

# Lint code
flake8 src/ tests/

# Type checking
mypy src/
```

## Monitoring and Maintenance

### Health Checks

The system includes health check endpoints:

- `GET /health` - Basic health check
- `GET /api/scheduler/status` - Scheduler status
- Database connection tests
- External service connectivity

### Logging

Logs are written to:

- Console output
- `logs/payroll_monitor.log` file
- Structured logging for production

### Data Cleanup

The system automatically cleans up old data:

- Monitoring runs older than 90 days
- Notifications older than 180 days
- Temporary files and caches

## Troubleshooting

### Common Issues

1. **Database Connection Errors**
   - Check database URL in environment variables
   - Ensure database server is running
   - Verify database permissions

2. **Web Scraping Failures**
   - Check internet connectivity
   - Verify target websites are accessible
   - Review Chrome/ChromeDriver installation

3. **Email Notification Failures**
   - Verify SMTP settings
   - Check email credentials
   - Review firewall settings

4. **Scheduler Issues**
   - Check system time and timezone
   - Verify cron/scheduler permissions
   - Review log files for errors

### Debug Mode

Enable debug logging:

```bash
export LOG_LEVEL=DEBUG
python main.py start
```

### Performance Tuning

- Adjust database connection pool size
- Configure monitoring timeouts
- Optimize retry attempts
- Tune AI analysis parameters

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass
6. Submit a pull request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

For support and questions:

- Create an issue in the GitHub repository
- Check the documentation
- Review the troubleshooting guide
- Contact the development team

## Roadmap

- [ ] Enhanced AI analysis capabilities
- [ ] Mobile dashboard application
- [ ] Integration with more notification platforms
- [ ] Advanced reporting and analytics
- [ ] Multi-tenant support
- [ ] API rate limiting and authentication
- [ ] Automated form field mapping
- [ ] Machine learning model training interface
