from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, ForeignKey, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

Base = declarative_base()


class Agency(Base):
    """Model for government agencies being monitored."""
    __tablename__ = "agencies"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    abbreviation = Column(String(10), nullable=True)
    agency_type = Column(String(20), nullable=False)  # 'federal', 'state', 'local'
    base_url = Column(String(500), nullable=False)
    prevailing_wage_url = Column(String(500), nullable=True)
    contact_phone = Column(String(20), nullable=True)
    contact_email = Column(String(100), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    forms = relationship("Form", back_populates="agency", cascade="all, delete-orphan")
    monitoring_runs = relationship("MonitoringRun", back_populates="agency")


class Form(Base):
    """Model for specific forms/reports from agencies."""
    __tablename__ = "forms"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    agency_id = Column(Integer, ForeignKey("agencies.id"), nullable=False)
    name = Column(String(100), nullable=False)  # e.g., "WH-347", "A1-131"
    title = Column(String(500), nullable=False)
    form_url = Column(String(500), nullable=True)
    instructions_url = Column(String(500), nullable=True)
    upload_portal_url = Column(String(500), nullable=True)
    check_frequency = Column(String(20), default="weekly")  # daily, weekly, monthly
    contact_email = Column(String(100), nullable=True)
    cpr_report_id = Column(String(50), nullable=True)  # CPR system identifier
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    last_checked = Column(DateTime, nullable=True)
    last_modified = Column(DateTime, nullable=True)
    
    # Relationships
    agency = relationship("Agency", back_populates="forms")
    changes = relationship("FormChange", back_populates="form", cascade="all, delete-orphan")
    monitoring_runs = relationship("MonitoringRun", back_populates="form")


class FormChange(Base):
    """Model for tracking changes to forms."""
    __tablename__ = "form_changes"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    form_id = Column(Integer, ForeignKey("forms.id"), nullable=False)
    change_type = Column(String(50), nullable=False)  # 'content', 'url', 'metadata', 'new_version'
    change_description = Column(Text, nullable=False)
    old_value = Column(Text, nullable=True)
    new_value = Column(Text, nullable=True)
    change_hash = Column(String(64), nullable=True)  # SHA256 hash for content changes
    detected_at = Column(DateTime, default=func.now())
    effective_date = Column(DateTime, nullable=True)
    agency_notification_date = Column(DateTime, nullable=True)
    severity = Column(String(20), default="medium")  # low, medium, high, critical
    status = Column(String(20), default="detected")  # detected, notified, evaluated, in_development, qa, eut, released
    impact_assessment = Column(JSON, nullable=True)  # JSON field for impact data
    
    # Relationships
    form = relationship("Form", back_populates="changes")
    notifications = relationship("Notification", back_populates="form_change")


class MonitoringRun(Base):
    """Model for tracking monitoring execution."""
    __tablename__ = "monitoring_runs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    agency_id = Column(Integer, ForeignKey("agencies.id"), nullable=False)
    form_id = Column(Integer, ForeignKey("forms.id"), nullable=True)
    started_at = Column(DateTime, default=func.now())
    completed_at = Column(DateTime, nullable=True)
    status = Column(String(20), default="running")  # running, completed, failed, timeout
    changes_detected = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)
    response_time_ms = Column(Integer, nullable=True)
    http_status_code = Column(Integer, nullable=True)
    content_hash = Column(String(64), nullable=True)
    
    # Relationships
    agency = relationship("Agency", back_populates="monitoring_runs")
    form = relationship("Form", back_populates="monitoring_runs")


class Notification(Base):
    """Model for tracking notifications sent."""
    __tablename__ = "notifications"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    form_change_id = Column(Integer, ForeignKey("form_changes.id"), nullable=False)
    notification_type = Column(String(20), nullable=False)  # email, slack, teams, webhook
    recipient = Column(String(255), nullable=False)
    subject = Column(String(500), nullable=True)
    message = Column(Text, nullable=False)
    sent_at = Column(DateTime, default=func.now())
    status = Column(String(20), default="pending")  # pending, sent, failed, bounced
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0)
    
    # Relationships
    form_change = relationship("FormChange", back_populates="notifications")


class Client(Base):
    """Model for tracking clients impacted by changes."""
    __tablename__ = "clients"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    client_id = Column(String(50), nullable=False, unique=True)  # CPR client ID
    icp_segment = Column(String(100), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    form_usage = relationship("ClientFormUsage", back_populates="client")


class ClientFormUsage(Base):
    """Model for tracking which clients use which forms."""
    __tablename__ = "client_form_usage"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False)
    form_id = Column(Integer, ForeignKey("forms.id"), nullable=False)
    usage_frequency = Column(String(20), nullable=True)  # weekly, bi-weekly, monthly
    last_used = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)
    
    # Relationships
    client = relationship("Client", back_populates="form_usage")
    form = relationship("Form")


class FieldMapping(Base):
    """Model for tracking field mappings between versions."""
    __tablename__ = "field_mappings"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    form_id = Column(Integer, ForeignKey("forms.id"), nullable=False)
    version = Column(String(20), nullable=False)
    field_name = Column(String(100), nullable=False)
    field_type = Column(String(50), nullable=False)
    is_required = Column(Boolean, default=False)
    validation_rules = Column(JSON, nullable=True)
    mapping_rules = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=func.now())
    
    # Relationships
    form = relationship("Form")


class WorkItem(Base):
    """Model for tracking development work items."""
    __tablename__ = "work_items"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    form_change_id = Column(Integer, ForeignKey("form_changes.id"), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    work_type = Column(String(50), nullable=False)  # evaluation, development, qa, eut
    status = Column(String(20), default="new")  # new, in_progress, completed, cancelled
    assigned_to = Column(String(100), nullable=True)
    estimated_effort_hours = Column(Integer, nullable=True)
    actual_effort_hours = Column(Integer, nullable=True)
    risk_level = Column(String(20), nullable=True)  # low, medium, high
    impact_level = Column(String(20), nullable=True)  # low, medium, high
    due_date = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=func.now())
    
    # Relationships
    form_change = relationship("FormChange")