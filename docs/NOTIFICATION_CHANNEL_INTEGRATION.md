# Notification Channel Integration

This document describes the enhanced notification channel integration system that supports multiple notification channels (email, Slack, Teams) with advanced features for the AI-powered compliance monitoring system.

## Overview

The notification channel integration system provides:

- **Multi-channel support**: Email, Slack, and Microsoft Teams
- **Role-based notifications**: Different templates and preferences for Product Managers and Business Analysts
- **Retry mechanisms**: Automatic retry with exponential backoff
- **Batching**: Prevent notification spam with intelligent batching
- **Business hours filtering**: Respect user preferences for notification timing
- **Severity filtering**: Send notifications based on change severity levels
- **Health monitoring**: Real-time status and connectivity testing

## Architecture

### Core Components

1. **ChannelIntegrationManager**: Main orchestrator for multi-channel notifications
2. **NotificationResult**: Structured results for notification attempts
3. **NotificationBatching**: Prevents spam with intelligent batching
4. **Enhanced Notifiers**: Email, Slack, and Teams notification services

### File Structure

```
src/notifications/
├── channel_integration.py          # Main integration module
├── channel_integration.test.py     # Unit tests
├── enhanced_notifier.py            # Enhanced notification manager
├── notifier.py                     # Base notification services
├── email_templates.py              # Role-based email templates
└── preference_manager.py           # User notification preferences

src/api/
└── notification_channels.py        # API endpoints for channel management
```

## Configuration

### Environment Variables

```bash
# Email Configuration (Required)
SMTP_SERVER=smtp.gmail.com
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
FROM_EMAIL=alerts@yourcompany.com
ALERT_EMAIL_1=admin@yourcompany.com
ALERT_EMAIL_2=backup-admin@yourcompany.com

# Slack Configuration (Optional)
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK
SLACK_CHANNEL=#payroll-alerts

# Microsoft Teams Configuration (Optional)
TEAMS_WEBHOOK_URL=https://yourcompany.webhook.office.com/webhookb2/YOUR/TEAMS/WEBHOOK
```

### YAML Configuration

```yaml
notification_settings:
  email:
    enabled: true
    smtp_server: "${SMTP_SERVER}"
    smtp_port: 587
    username: "${SMTP_USERNAME}"
    password: "${SMTP_PASSWORD}"
    from_address: "${FROM_EMAIL}"
    to_addresses:
      - "${ALERT_EMAIL_1}"
      - "${ALERT_EMAIL_2}"
  
  slack:
    enabled: false
    webhook_url: "${SLACK_WEBHOOK_URL}"
    channel: "#payroll-alerts"
  
  teams:
    enabled: false
    webhook_url: "${TEAMS_WEBHOOK_URL}"
```

## Usage

### Basic Channel Integration

```python
from src.notifications.channel_integration import ChannelIntegrationManager

# Initialize the channel manager
manager = ChannelIntegrationManager()

# Send notification through multiple channels
change_data = {
    'agency_name': 'Department of Labor',
    'form_name': 'WH-347',
    'severity': 'high',
    'change_description': 'Updated wage determination requirements'
}

user_preferences = [
    {
        'notification_type': 'email',
        'is_enabled': True,
        'change_severity': 'all'
    },
    {
        'notification_type': 'slack',
        'is_enabled': True,
        'change_severity': 'high'
    }
]

results = await manager.send_multi_channel_notification(
    change_data, user_preferences, user
)
```

### Testing Channel Connectivity

```python
# Test all channels
connectivity_results = await manager.test_channel_connectivity()

# Get channel status
status = manager.get_channel_status()
```

### Using the API

#### Get Channel Status
```bash
GET /api/notification-channels/status
```

#### Test Connectivity
```bash
POST /api/notification-channels/test-connectivity
```

#### Send Test Notification
```bash
POST /api/notification-channels/test-notification
Content-Type: application/json

{
    "channel": "slack",
    "test_data": {
        "agency_name": "Test Agency",
        "form_name": "TEST-001",
        "severity": "medium"
    }
}
```

#### Health Check
```bash
GET /api/notification-channels/health
```

## Features

### 1. Multi-Channel Support

The system supports three notification channels:

- **Email**: Rich HTML templates with role-based content
- **Slack**: Formatted messages with attachments and color coding
- **Teams**: Message cards with actionable buttons and rich formatting

### 2. Role-Based Templates

Different notification templates for different user roles:

- **Product Manager**: High-level overview with business impact
- **Business Analyst**: Technical details with implementation guidance

### 3. Retry Mechanism

Automatic retry with exponential backoff:

```python
retry_config = {
    'max_retries': 3,
    'retry_delay': 5,  # seconds
    'backoff_multiplier': 2
}
```

### 4. Notification Batching

Prevents notification spam:

```python
batching = NotificationBatching(
    batch_size=5,      # Max notifications per batch
    batch_window=300   # 5-minute window
)
```

### 5. Business Hours Filtering

Respects user preferences for notification timing:

```python
if preference.get('business_hours_only', False):
    now = datetime.now()
    if now.weekday() >= 5:  # Weekend
        return False
    if now.hour < 9 or now.hour > 17:  # Outside business hours
        return False
```

### 6. Severity Filtering

Send notifications based on change severity:

```python
severity_levels = ['low', 'medium', 'high', 'critical']
pref_level = severity_levels.index(pref_severity)
change_level = severity_levels.index(change_severity)

if change_level < pref_level:
    return False  # Don't send notification
```

## API Endpoints

### Channel Management

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/notification-channels/status` | GET | Get channel status |
| `/api/notification-channels/configuration` | GET | Get channel configuration |
| `/api/notification-channels/enable-channel` | POST | Enable a channel |
| `/api/notification-channels/disable-channel` | POST | Disable a channel |

### Testing and Monitoring

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/notification-channels/test-connectivity` | POST | Test all channels |
| `/api/notification-channels/test-notification` | POST | Send test notification |
| `/api/notification-channels/health` | GET | Health check |
| `/api/notification-channels/batching-status` | GET | Get batching status |
| `/api/notification-channels/clear-batch` | POST | Clear batched notifications |

## Error Handling

### NotificationResult Structure

```python
@dataclass
class NotificationResult:
    channel: str
    success: bool
    recipient: str
    message_id: Optional[str] = None
    error_message: Optional[str] = None
    retry_count: int = 0
    sent_at: Optional[datetime] = None
```

### Common Error Scenarios

1. **Channel Not Available**: Channel not configured or disabled
2. **Authentication Failed**: Invalid credentials for email/Slack/Teams
3. **Network Error**: Connection timeout or network issues
4. **Rate Limiting**: Too many requests to external services
5. **Invalid Configuration**: Missing required configuration parameters

## Testing

### Unit Tests

Run the comprehensive test suite:

```bash
pytest src/notifications/channel_integration.test.py -v
```

### Integration Tests

Test the full notification flow:

```python
# Test multi-channel notification
results = await manager.send_multi_channel_notification(
    test_data, preferences, user
)

# Verify results
assert len(results) == 3  # email, slack, teams
assert all(result.success for result in results)
```

### Manual Testing

1. **Email Testing**: Send test email to verify SMTP configuration
2. **Slack Testing**: Send test message to verify webhook URL
3. **Teams Testing**: Send test card to verify webhook URL

## Monitoring and Logging

### Log Levels

- **INFO**: Successful notifications and configuration changes
- **WARNING**: Retry attempts and configuration issues
- **ERROR**: Failed notifications and connectivity problems

### Metrics

Track notification performance:

- Success/failure rates by channel
- Average delivery time
- Retry frequency
- Channel availability

## Security Considerations

1. **Environment Variables**: Store sensitive credentials in environment variables
2. **Webhook URLs**: Keep webhook URLs secure and rotate regularly
3. **Rate Limiting**: Implement rate limiting to prevent abuse
4. **Access Control**: Restrict channel management to admin users
5. **Audit Logging**: Log all notification attempts for compliance

## Troubleshooting

### Common Issues

1. **Email Not Sending**
   - Check SMTP server configuration
   - Verify credentials and port settings
   - Check firewall/network connectivity

2. **Slack Notifications Failing**
   - Verify webhook URL is correct
   - Check Slack app permissions
   - Ensure channel exists and bot has access

3. **Teams Notifications Failing**
   - Verify webhook URL format
   - Check Teams app permissions
   - Ensure webhook is properly configured

4. **High Retry Rates**
   - Check network connectivity
   - Verify external service status
   - Review rate limiting settings

### Debug Mode

Enable debug logging:

```python
import logging
logging.getLogger('src.notifications').setLevel(logging.DEBUG)
```

## Future Enhancements

1. **Additional Channels**: SMS, push notifications, webhooks
2. **Advanced Batching**: Smart batching based on content similarity
3. **Template Customization**: User-defined notification templates
4. **Delivery Tracking**: Track notification delivery and read receipts
5. **Analytics Dashboard**: Real-time notification analytics
6. **A/B Testing**: Test different notification formats and timing

## Conclusion

The notification channel integration system provides a robust, scalable solution for multi-channel notifications with advanced features like retry mechanisms, batching, and role-based templates. The system is designed to be easily extensible for additional channels and features while maintaining high reliability and performance. 