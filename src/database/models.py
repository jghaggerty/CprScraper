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
    
    # AI Analysis Fields
    ai_confidence_score = Column(Integer, nullable=True)  # 0-100 confidence percentage
    ai_change_category = Column(String(50), nullable=True)  # 'form_update', 'requirement_change', 'logic_modification'
    ai_severity_score = Column(Integer, nullable=True)  # 0-100 severity score from AI
    ai_reasoning = Column(Text, nullable=True)  # LLM explanation of the analysis
    ai_semantic_similarity = Column(Integer, nullable=True)  # 0-100 semantic similarity score
    ai_analysis_metadata = Column(JSON, nullable=True)  # Model versions, processing time, etc.
    ai_analysis_timestamp = Column(DateTime, nullable=True)  # When AI analysis was performed
    is_cosmetic_change = Column(Boolean, default=False)  # AI determination if change is cosmetic
    
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
    status = Column(String(20), default="pending")  # pending, sending, delivered, failed, bounced, retrying, expired, cancelled
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0)
    delivery_time = Column(Integer, nullable=True)  # Delivery time in seconds
    response_data = Column(JSON, nullable=True)  # Response data from delivery service
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
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


class User(Base):
    """Model for system users with role-based access control."""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), nullable=False, unique=True)
    email = Column(String(100), nullable=False, unique=True)
    first_name = Column(String(50), nullable=False)
    last_name = Column(String(50), nullable=False)
    password_hash = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    last_login = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    user_roles = relationship("UserRole", back_populates="user", cascade="all, delete-orphan")
    dashboard_preferences = relationship("UserDashboardPreference", back_populates="user", cascade="all, delete-orphan")
    notification_preferences = relationship("UserNotificationPreference", back_populates="user", cascade="all, delete-orphan")


class Role(Base):
    """Model for user roles in the system."""
    __tablename__ = "roles"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), nullable=False, unique=True)  # 'product_manager', 'business_analyst', 'admin'
    display_name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    permissions = Column(JSON, nullable=True)  # JSON array of permission strings
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    user_roles = relationship("UserRole", back_populates="role", cascade="all, delete-orphan")


class UserRole(Base):
    """Model for user-role assignments."""
    __tablename__ = "user_roles"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    role_id = Column(Integer, ForeignKey("roles.id"), nullable=False)
    assigned_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    assigned_at = Column(DateTime, default=func.now())
    expires_at = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)
    
    # Relationships
    user = relationship("User", back_populates="user_roles", foreign_keys=[user_id])
    role = relationship("Role", back_populates="user_roles")
    assigned_by_user = relationship("User", foreign_keys=[assigned_by])


class UserDashboardPreference(Base):
    """Model for storing user dashboard preferences and layouts."""
    __tablename__ = "user_dashboard_preferences"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    preference_key = Column(String(100), nullable=False)  # 'layout', 'widgets', 'filters', 'theme'
    preference_value = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="dashboard_preferences")


class UserNotificationPreference(Base):
    """Model for storing user notification preferences."""
    __tablename__ = "user_notification_preferences"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    notification_type = Column(String(50), nullable=False)  # 'email', 'slack', 'teams', 'webhook'
    change_severity = Column(String(20), nullable=True)  # 'low', 'medium', 'high', 'critical', 'all'
    frequency = Column(String(20), nullable=False)  # 'immediate', 'hourly', 'daily', 'weekly'
    is_enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="notification_preferences")