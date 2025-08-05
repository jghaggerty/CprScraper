-- Migration: Add notification delivery tracking fields
-- Date: 2024-01-15
-- Description: Add delivery_time, response_data, created_at, and updated_at fields to notifications table

-- Add new columns to notifications table
ALTER TABLE notifications 
ADD COLUMN delivery_time INTEGER NULL COMMENT 'Delivery time in seconds',
ADD COLUMN response_data JSON NULL COMMENT 'Response data from delivery service',
ADD COLUMN created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT 'Record creation timestamp',
ADD COLUMN updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT 'Record update timestamp';

-- Update status enum values to include new statuses
-- Note: This is a comment as MySQL doesn't have true enums in this context
-- The status field accepts: pending, sending, delivered, failed, bounced, retrying, expired, cancelled

-- Create index on status for faster queries
CREATE INDEX idx_notifications_status ON notifications(status);

-- Create index on sent_at for time-based queries
CREATE INDEX idx_notifications_sent_at ON notifications(sent_at);

-- Create index on retry_count for retry analysis
CREATE INDEX idx_notifications_retry_count ON notifications(retry_count);

-- Create composite index for delivery analytics
CREATE INDEX idx_notifications_delivery_analytics ON notifications(status, sent_at, retry_count);

-- Add comments to existing columns for clarity
ALTER TABLE notifications 
MODIFY COLUMN status VARCHAR(20) DEFAULT 'pending' 
COMMENT 'pending, sending, delivered, failed, bounced, retrying, expired, cancelled';

-- Update existing records to have created_at and updated_at timestamps
UPDATE notifications 
SET created_at = sent_at, 
    updated_at = sent_at 
WHERE created_at IS NULL OR updated_at IS NULL; 