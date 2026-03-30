"""
SQLAlchemy ORM models for MentorMe.

Tables
------
users                – all platform users (mentee / mentor / admin)
mentorship_requests  – mentee → mentor connection requests
sessions             – booked 1-on-1 sessions
session_messages     – in-session chat messages
ratings              – post-session ratings (one per user per session)
notifications        – in-app notifications per user
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.db.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


# ── Users ─────────────────────────────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=_uuid)
    supabase_id = Column(String(64), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    role = Column(Enum("mentee", "mentor", "admin", name="user_role_enum"), nullable=False, default="mentee")
    avatar_url = Column(String(512), nullable=True)
    bio = Column(Text, nullable=True)
    gender = Column(String(50), nullable=True)
    skills = Column(Text, nullable=True)
    goals = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    verification_status = Column(Enum("not_required", "pending", "approved", "rejected", name="verification_status_enum"), nullable=False, default="not_required")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    mentor_sessions = relationship("Session", foreign_keys="Session.mentor_id", back_populates="mentor")
    mentee_sessions = relationship("Session", foreign_keys="Session.mentee_id", back_populates="mentee")
    sent_requests = relationship("MentorshipRequest", foreign_keys="MentorshipRequest.mentee_id", back_populates="mentee")
    received_requests = relationship("MentorshipRequest", foreign_keys="MentorshipRequest.mentor_id", back_populates="mentor")
    ratings_given = relationship("Rating", foreign_keys="Rating.rater_id", back_populates="rater")
    messages = relationship("SessionMessage", back_populates="sender")
    notifications = relationship("Notification", foreign_keys="Notification.user_id", back_populates="user")


# ── Mentorship requests ───────────────────────────────────────────────────────

class MentorshipRequest(Base):
    __tablename__ = "mentorship_requests"

    id = Column(String(36), primary_key=True, default=_uuid)
    mentee_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    mentor_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    topic = Column(String(255), nullable=False)
    message = Column(Text, nullable=True)
    preferred_time = Column(DateTime, nullable=True)
    status = Column(Enum("pending", "accepted", "declined", name="request_status_enum"), default="pending", nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    mentee = relationship("User", foreign_keys=[mentee_id], back_populates="sent_requests")
    mentor = relationship("User", foreign_keys=[mentor_id], back_populates="received_requests")


# ── Sessions ──────────────────────────────────────────────────────────────────

class Session(Base):
    __tablename__ = "sessions"

    id = Column(String(36), primary_key=True, default=_uuid)
    mentor_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    mentee_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    topic = Column(String(255), nullable=False)
    scheduled_at = Column(DateTime, nullable=False)
    duration_minutes = Column(Integer, default=60)
    status = Column(
        Enum("scheduled", "in_progress", "completed", "cancelled", name="session_status_enum"),
        default="scheduled",
        nullable=False,
    )
    video_room_url = Column(String(512), nullable=True)
    video_room_name = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    mentor = relationship("User", foreign_keys=[mentor_id], back_populates="mentor_sessions")
    mentee = relationship("User", foreign_keys=[mentee_id], back_populates="mentee_sessions")
    messages = relationship("SessionMessage", back_populates="session", cascade="all, delete-orphan")
    ratings = relationship("Rating", back_populates="session", cascade="all, delete-orphan")


# ── Session messages ──────────────────────────────────────────────────────────

class SessionMessage(Base):
    __tablename__ = "session_messages"

    id = Column(String(36), primary_key=True, default=_uuid)
    session_id = Column(String(36), ForeignKey("sessions.id"), nullable=False)
    sender_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    text = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    session = relationship("Session", back_populates="messages")
    sender = relationship("User", back_populates="messages")


# ── Ratings ───────────────────────────────────────────────────────────────────

class Rating(Base):
    __tablename__ = "ratings"
    __table_args__ = (UniqueConstraint("session_id", "rater_id", name="uq_session_rater"),)

    id = Column(String(36), primary_key=True, default=_uuid)
    session_id = Column(String(36), ForeignKey("sessions.id"), nullable=False)
    rater_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    rated_user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    rating = Column(Integer, nullable=False)
    comment = Column(Text, nullable=True)
    tags = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    session = relationship("Session", back_populates="ratings")
    rater = relationship("User", foreign_keys=[rater_id], back_populates="ratings_given")
    rated_user = relationship("User", foreign_keys=[rated_user_id])


# ── Notifications ─────────────────────────────────────────────────────────────

class Notification(Base):
    __tablename__ = "notifications"

    id = Column(String(36), primary_key=True, default=_uuid)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    type = Column(
        Enum("message", "session", "request", "system", name="notification_type_enum"),
        nullable=False,
        default="system",
    )
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    read = Column(Boolean, default=False)
    related_id = Column(String(36), nullable=True)   # session_id, request_id, etc.
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", foreign_keys=[user_id], back_populates="notifications")


# ── Mentor Application ────────────────────────────────────────────────────────

class MentorApplication(Base):
    __tablename__ = "mentor_applications"

    id = Column(String(36), primary_key=True, default=_uuid)
    mentor_id = Column(String(36), ForeignKey("users.id"), nullable=False, unique=True, index=True)
    
    # Step 1: Personal Information
    phone_number = Column(String(20), nullable=True)
    location = Column(String(255), nullable=True)
    gender = Column(String(50), nullable=True)
    step_1_completed = Column(Boolean, default=False)
    
    # Step 2: Professional Background
    job_title = Column(String(255), nullable=True)
    company = Column(String(255), nullable=True)
    years_experience = Column(Integer, nullable=True)
    linkedin_url = Column(String(512), nullable=True)
    skills = Column(Text, nullable=True)  # Comma-separated
    professional_bio = Column(Text, nullable=True)
    step_2_completed = Column(Boolean, default=False)
    
    # Step 3: Document Upload
    id_document_url = Column(String(512), nullable=True)  # NIN, passport, or driver's license
    id_document_type = Column(String(50), nullable=True)  # "nin", "passport", "driver_license"
    professional_certificate_url = Column(String(512), nullable=True)
    step_3_completed = Column(Boolean, default=False)
    
    # Step 4: Review and Submit
    submitted_at = Column(DateTime, nullable=True)
    status = Column(
        Enum("draft", "step_1", "step_2", "step_3", "review", "submitted", "approved", "rejected", name="application_status_enum"),
        default="draft",
        nullable=False
    )
    
    # Admin review
    admin_notes = Column(Text, nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    reviewed_by = Column(String(36), ForeignKey("users.id"), nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    mentor = relationship("User", foreign_keys=[mentor_id], primaryjoin="MentorApplication.mentor_id == User.id")
    reviewer = relationship("User", foreign_keys=[reviewed_by])
