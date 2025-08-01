-- Migration: Add AI Analysis Fields to FormChange Table
-- Description: Adds columns to store AI analysis metadata for enhanced change detection
-- Version: 2024.01.15_001
-- Author: AI Analysis System

-- Add AI analysis columns to form_changes table
ALTER TABLE form_changes ADD COLUMN IF NOT EXISTS ai_confidence_score INTEGER;
ALTER TABLE form_changes ADD COLUMN IF NOT EXISTS ai_change_category VARCHAR(50);
ALTER TABLE form_changes ADD COLUMN IF NOT EXISTS ai_severity_score INTEGER;
ALTER TABLE form_changes ADD COLUMN IF NOT EXISTS ai_reasoning TEXT;
ALTER TABLE form_changes ADD COLUMN IF NOT EXISTS ai_semantic_similarity INTEGER;
ALTER TABLE form_changes ADD COLUMN IF NOT EXISTS ai_analysis_metadata JSON;
ALTER TABLE form_changes ADD COLUMN IF NOT EXISTS ai_analysis_timestamp TIMESTAMP;
ALTER TABLE form_changes ADD COLUMN IF NOT EXISTS is_cosmetic_change BOOLEAN DEFAULT FALSE;

-- Add comments for documentation
COMMENT ON COLUMN form_changes.ai_confidence_score IS 'AI confidence percentage (0-100) in the analysis results';
COMMENT ON COLUMN form_changes.ai_change_category IS 'AI-determined change category (form_update, requirement_change, logic_modification, cosmetic_change)';
COMMENT ON COLUMN form_changes.ai_severity_score IS 'AI-assigned severity score (0-100) for prioritization';
COMMENT ON COLUMN form_changes.ai_reasoning IS 'LLM-generated explanation of the analysis and reasoning';
COMMENT ON COLUMN form_changes.ai_semantic_similarity IS 'Semantic similarity percentage (0-100) between document versions';
COMMENT ON COLUMN form_changes.ai_analysis_metadata IS 'JSON metadata including model versions, processing time, confidence breakdown';
COMMENT ON COLUMN form_changes.ai_analysis_timestamp IS 'Timestamp when AI analysis was performed';
COMMENT ON COLUMN form_changes.is_cosmetic_change IS 'Boolean indicating if the change is purely cosmetic/formatting';

-- Create indexes for common query patterns
CREATE INDEX IF NOT EXISTS idx_form_changes_ai_category ON form_changes(ai_change_category);
CREATE INDEX IF NOT EXISTS idx_form_changes_ai_severity ON form_changes(ai_severity_score DESC);
CREATE INDEX IF NOT EXISTS idx_form_changes_ai_confidence ON form_changes(ai_confidence_score DESC);
CREATE INDEX IF NOT EXISTS idx_form_changes_cosmetic ON form_changes(is_cosmetic_change);
CREATE INDEX IF NOT EXISTS idx_form_changes_ai_timestamp ON form_changes(ai_analysis_timestamp DESC);

-- Create composite index for AI analysis queries
CREATE INDEX IF NOT EXISTS idx_form_changes_ai_analysis_composite ON form_changes(
    ai_change_category, 
    ai_severity_score DESC, 
    ai_analysis_timestamp DESC
) WHERE ai_confidence_score IS NOT NULL;

-- Add check constraints for data validation
ALTER TABLE form_changes ADD CONSTRAINT chk_ai_confidence_score 
    CHECK (ai_confidence_score IS NULL OR (ai_confidence_score >= 0 AND ai_confidence_score <= 100));

ALTER TABLE form_changes ADD CONSTRAINT chk_ai_severity_score 
    CHECK (ai_severity_score IS NULL OR (ai_severity_score >= 0 AND ai_severity_score <= 100));

ALTER TABLE form_changes ADD CONSTRAINT chk_ai_semantic_similarity 
    CHECK (ai_semantic_similarity IS NULL OR (ai_semantic_similarity >= 0 AND ai_semantic_similarity <= 100));

ALTER TABLE form_changes ADD CONSTRAINT chk_ai_change_category 
    CHECK (ai_change_category IS NULL OR ai_change_category IN (
        'form_update', 'requirement_change', 'logic_modification', 'cosmetic_change'
    ));

-- Update existing records to set default values for new fields
UPDATE form_changes 
SET is_cosmetic_change = FALSE 
WHERE is_cosmetic_change IS NULL;

-- Create a view for AI analysis summary
CREATE OR REPLACE VIEW ai_analysis_summary AS
SELECT 
    f.name as form_name,
    a.name as agency_name,
    fc.id as change_id,
    fc.detected_at,
    fc.ai_change_category,
    fc.severity,
    fc.ai_severity_score,
    fc.ai_confidence_score,
    fc.ai_semantic_similarity,
    fc.is_cosmetic_change,
    fc.ai_analysis_timestamp,
    CASE 
        WHEN fc.ai_severity_score >= 80 THEN 'High Priority'
        WHEN fc.ai_severity_score >= 50 THEN 'Medium Priority'
        WHEN fc.ai_severity_score >= 20 THEN 'Low Priority'
        ELSE 'Minimal Priority'
    END as priority_level
FROM form_changes fc
JOIN forms f ON fc.form_id = f.id
JOIN agencies a ON f.agency_id = a.id
WHERE fc.ai_confidence_score IS NOT NULL
ORDER BY fc.ai_severity_score DESC, fc.detected_at DESC;

COMMENT ON VIEW ai_analysis_summary IS 'Summary view of all AI-analyzed changes with priority categorization';

-- Create function to get AI analysis statistics
CREATE OR REPLACE FUNCTION get_ai_analysis_stats(days_back INTEGER DEFAULT 30)
RETURNS TABLE(
    total_analyses BIGINT,
    high_priority_changes BIGINT,
    medium_priority_changes BIGINT,
    low_priority_changes BIGINT,
    cosmetic_changes BIGINT,
    avg_confidence_score NUMERIC,
    avg_semantic_similarity NUMERIC,
    most_common_category TEXT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        COUNT(*) as total_analyses,
        COUNT(*) FILTER (WHERE ai_severity_score >= 80) as high_priority_changes,
        COUNT(*) FILTER (WHERE ai_severity_score >= 50 AND ai_severity_score < 80) as medium_priority_changes,
        COUNT(*) FILTER (WHERE ai_severity_score < 50 AND ai_severity_score >= 20) as low_priority_changes,
        COUNT(*) FILTER (WHERE is_cosmetic_change = TRUE) as cosmetic_changes,
        ROUND(AVG(ai_confidence_score), 2) as avg_confidence_score,
        ROUND(AVG(ai_semantic_similarity), 2) as avg_semantic_similarity,
        MODE() WITHIN GROUP (ORDER BY ai_change_category) as most_common_category
    FROM form_changes 
    WHERE ai_analysis_timestamp >= CURRENT_DATE - INTERVAL '%s days'
    AND ai_confidence_score IS NOT NULL;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION get_ai_analysis_stats IS 'Returns comprehensive statistics about AI analysis results for the specified time period';

-- Grant necessary permissions (adjust roles as needed for your setup)
-- GRANT SELECT ON ai_analysis_summary TO monitoring_role;
-- GRANT EXECUTE ON FUNCTION get_ai_analysis_stats TO monitoring_role;

-- Log migration completion
INSERT INTO migration_log (migration_name, applied_at, description) 
VALUES (
    'add_ai_analysis_fields', 
    CURRENT_TIMESTAMP, 
    'Added AI analysis fields to form_changes table with indexes, constraints, views, and statistics function'
) ON CONFLICT (migration_name) DO UPDATE SET
    applied_at = CURRENT_TIMESTAMP,
    description = EXCLUDED.description;