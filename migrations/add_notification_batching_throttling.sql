-- Migration: Add notification batching and throttling tracking
-- Date: 2024-01-XX
-- Description: Add tables and fields for tracking notification batching and throttling

-- Add batching and throttling fields to notifications table
ALTER TABLE notifications ADD COLUMN batch_id VARCHAR(255) NULL;
ALTER TABLE notifications ADD COLUMN is_batch BOOLEAN DEFAULT FALSE;
ALTER TABLE notifications ADD COLUMN batch_size INTEGER NULL;
ALTER TABLE notifications ADD COLUMN throttled BOOLEAN DEFAULT FALSE;
ALTER TABLE notifications ADD COLUMN throttle_reason VARCHAR(255) NULL;

-- Create index for batch_id
CREATE INDEX idx_notifications_batch_id ON notifications(batch_id);

-- Create table for notification batches
CREATE TABLE notification_batches (
    id VARCHAR(255) PRIMARY KEY,
    user_id INTEGER NOT NULL,
    channel VARCHAR(50) NOT NULL,
    severity VARCHAR(20) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    priority_score DECIMAL(5,2) DEFAULT 0.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    scheduled_for TIMESTAMP NULL,
    sent_at TIMESTAMP NULL,
    batch_size INTEGER DEFAULT 0,
    consolidated_subject TEXT NULL,
    consolidated_message TEXT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Create indexes for notification_batches
CREATE INDEX idx_notification_batches_user_id ON notification_batches(user_id);
CREATE INDEX idx_notification_batches_status ON notification_batches(status);
CREATE INDEX idx_notification_batches_created_at ON notification_batches(created_at);

-- Create table for throttling metrics
CREATE TABLE throttle_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    channel VARCHAR(50) NOT NULL,
    notifications_sent INTEGER DEFAULT 0,
    last_notification_time TIMESTAMP NULL,
    hourly_count INTEGER DEFAULT 0,
    daily_count INTEGER DEFAULT 0,
    burst_count INTEGER DEFAULT 0,
    burst_start_time TIMESTAMP NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    UNIQUE(user_id, channel)
);

-- Create indexes for throttle_metrics
CREATE INDEX idx_throttle_metrics_user_id ON throttle_metrics(user_id);
CREATE INDEX idx_throttle_metrics_channel ON throttle_metrics(channel);
CREATE INDEX idx_throttle_metrics_last_notification_time ON throttle_metrics(last_notification_time);

-- Create table for batching and throttling configuration
CREATE TABLE notification_config (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    config_type VARCHAR(50) NOT NULL, -- 'batching' or 'throttling'
    config_key VARCHAR(100) NOT NULL,
    config_value TEXT NOT NULL,
    description TEXT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(config_type, config_key)
);

-- Insert default batching configuration
INSERT INTO notification_config (config_type, config_key, config_value, description) VALUES
('batching', 'enabled', 'true', 'Enable notification batching'),
('batching', 'max_batch_size', '10', 'Maximum notifications per batch'),
('batching', 'max_batch_delay_minutes', '30', 'Maximum delay before sending batch'),
('batching', 'priority_override', 'false', 'Send high priority notifications immediately'),
('batching', 'group_by_user', 'true', 'Group notifications by user'),
('batching', 'group_by_severity', 'true', 'Group notifications by severity'),
('batching', 'group_by_channel', 'true', 'Group notifications by channel');

-- Insert default throttling configuration
INSERT INTO notification_config (config_type, config_key, config_value, description) VALUES
('throttling', 'enabled', 'true', 'Enable notification throttling'),
('throttling', 'rate_limit_per_hour', '50', 'Maximum notifications per hour'),
('throttling', 'rate_limit_per_day', '200', 'Maximum notifications per day'),
('throttling', 'cooldown_minutes', '5', 'Minimum minutes between notifications'),
('throttling', 'burst_limit', '10', 'Maximum notifications in burst'),
('throttling', 'burst_window_minutes', '15', 'Burst window in minutes'),
('throttling', 'daily_limit', '100', 'Maximum notifications per day'),
('throttling', 'exempt_high_priority', 'true', 'Exempt high priority from throttling'),
('throttling', 'exempt_critical_severity', 'true', 'Exempt critical severity from throttling');

-- Create table for batch notifications (many-to-many relationship)
CREATE TABLE batch_notifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    batch_id VARCHAR(255) NOT NULL,
    notification_id INTEGER NOT NULL,
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (batch_id) REFERENCES notification_batches(id) ON DELETE CASCADE,
    FOREIGN KEY (notification_id) REFERENCES notifications(id) ON DELETE CASCADE,
    UNIQUE(batch_id, notification_id)
);

-- Create indexes for batch_notifications
CREATE INDEX idx_batch_notifications_batch_id ON batch_notifications(batch_id);
CREATE INDEX idx_batch_notifications_notification_id ON batch_notifications(notification_id);

-- Create table for throttling events (audit trail)
CREATE TABLE throttle_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    channel VARCHAR(50) NOT NULL,
    event_type VARCHAR(50) NOT NULL, -- 'throttled', 'rate_limit_exceeded', 'cooldown_active', etc.
    reason TEXT NULL,
    notification_data TEXT NULL, -- JSON data about the notification
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Create indexes for throttle_events
CREATE INDEX idx_throttle_events_user_id ON throttle_events(user_id);
CREATE INDEX idx_throttle_events_event_type ON throttle_events(event_type);
CREATE INDEX idx_throttle_events_created_at ON throttle_events(created_at);

-- Add comments to existing notifications table
COMMENT ON COLUMN notifications.batch_id IS 'ID of the batch this notification belongs to';
COMMENT ON COLUMN notifications.is_batch IS 'Whether this is a consolidated batch notification';
COMMENT ON COLUMN notifications.batch_size IS 'Number of notifications in the batch';
COMMENT ON COLUMN notifications.throttled IS 'Whether this notification was throttled';
COMMENT ON COLUMN notifications.throttle_reason IS 'Reason for throttling if applicable'; 