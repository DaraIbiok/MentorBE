"""
Pydantic v2 schemas — all responses use camelCase to match frontend expectations.
"""

from __future__ import annotations
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator, model_serializer
import json


def _split(v: str | None) -> List[str]:
    if not v:
        return []
    return [s.strip() for s in v.split(",") if s.strip()]


# ── Base model with camelCase output ──────────────────────────────────────────

class CamelModel(BaseModel):
    model_config = {
        "from_attributes": True,
        "populate_by_name": True,
        "alias_generator": None,
    }

    def model_dump(self, **kwargs):
        # Always output camelCase
        kwargs.setdefault("by_alias", True)
        return super().model_dump(**kwargs)


# ── User / Profile ─────────────────────────────────────────────────────────────

class UserOut(CamelModel):
    id: str
    email: str
    name: str
    role: str
    avatar_url: Optional[str] = Field(None, alias="avatarUrl", serialization_alias="avatarUrl")
    bio: Optional[str] = None
    gender: Optional[str] = None
    skills: List[str] = []
    goals: List[str] = []
    created_at: datetime = Field(alias="createdAt", serialization_alias="createdAt")

    model_config = {
        "from_attributes": True,
        "populate_by_name": True,
    }

    @classmethod
    def from_orm_user(cls, user) -> "UserOut":
        return cls.model_construct(
            id=user.id,
            email=user.email,
            name=user.name,
            role=user.role,
            avatar_url=user.avatar_url,
            bio=user.bio,
            gender=user.gender,
            skills=_split(user.skills),
            goals=_split(user.goals),
            created_at=user.created_at,
        )

    def model_dump(self, **kwargs):
        d = super(CamelModel, self).model_dump(**kwargs)
        # Manually map snake to camel
        result = {}
        for k, v in d.items():
            camel = _to_camel(k)
            result[camel] = v
        return result


def _to_camel(snake: str) -> str:
    parts = snake.split("_")
    return parts[0] + "".join(p.capitalize() for p in parts[1:])


class ProfileUpdateIn(BaseModel):
    name: Optional[str] = None
    avatar_url: Optional[str] = Field(None, alias="avatarUrl")
    bio: Optional[str] = None
    gender: Optional[str] = None
    skills: Optional[List[str]] = None
    goals: Optional[List[str]] = None
    role: Optional[str] = None

    model_config = {"populate_by_name": True}


# ── Mentor ─────────────────────────────────────────────────────────────────────

class MentorOut(BaseModel):
    id: str
    name: str
    email: str
    avatarUrl: Optional[str] = None
    bio: Optional[str] = None
    skills: List[str] = []
    averageRating: Optional[float] = None
    ratingCount: int = 0
    matchScore: int = 0  # ← ADD THIS
    
    model_config = {"from_attributes": True, "populate_by_name": True}


# ── Requests ───────────────────────────────────────────────────────────────────

class MentorshipRequestIn(BaseModel):
    mentor_id: str = Field(alias="mentorId")
    topic: str
    message: Optional[str] = None
    preferred_time: Optional[datetime] = Field(None, alias="preferredTime")

    model_config = {"populate_by_name": True}


class MentorshipRequestStatusIn(BaseModel):
    status: str


class MenteeSnippet(BaseModel):
    id: str
    name: Optional[str] = None
    avatarUrl: Optional[str] = None

    model_config = {"from_attributes": True}


class MentorshipRequestOut(BaseModel):
    id: str
    menteeId: str
    mentorId: str
    topic: str
    message: Optional[str] = None
    preferredTime: Optional[datetime] = None
    status: str
    createdAt: datetime
    mentee: MenteeSnippet

    model_config = {"from_attributes": True, "populate_by_name": True}


# ── Sessions ───────────────────────────────────────────────────────────────────

class UserSnippet(BaseModel):
    id: str
    name: Optional[str] = None
    avatarUrl: Optional[str] = None

    model_config = {"from_attributes": True}


class SessionCreateIn(BaseModel):
    mentor_id: str = Field(alias="mentorId")
    topic: str
    scheduled_at: datetime = Field(alias="scheduledAt")
    duration_minutes: int = Field(60, alias="durationMinutes")

    model_config = {"populate_by_name": True}


class SessionStatusIn(BaseModel):
    status: str


class SessionOut(BaseModel):
    id: str
    mentorId: str
    menteeId: str
    topic: str
    scheduledAt: datetime
    durationMinutes: int
    status: str
    videoRoomUrl: Optional[str] = None
    mentor: UserSnippet
    mentee: UserSnippet

    model_config = {"from_attributes": True, "populate_by_name": True}


class MessageOut(BaseModel):
    id: str
    sessionId: str
    senderId: str
    text: str
    createdAt: datetime
    sender: UserSnippet

    model_config = {"from_attributes": True, "populate_by_name": True}


class SessionDetailOut(SessionOut):
    messages: List[MessageOut] = []


class MessageIn(BaseModel):
    text: str


class VideoRoomOut(BaseModel):
    url: str


# ── Ratings ────────────────────────────────────────────────────────────────────

class RatingIn(BaseModel):
    rating: int = Field(..., ge=1, le=5)
    comment: Optional[str] = None
    tags: List[str] = []


class RatingOut(BaseModel):
    id: str
    rating: int
    comment: Optional[str] = None
    tags: List[str] = []
    createdAt: datetime
    rater: UserSnippet
    session: Optional[dict] = None

    model_config = {"from_attributes": True, "populate_by_name": True}


# ── Mentor → mentees ───────────────────────────────────────────────────────────

class NextSessionSnippet(BaseModel):
    id: str
    topic: str
    scheduledAt: datetime
    durationMinutes: int


class MenteeListItem(BaseModel):
    id: str
    name: Optional[str] = None
    avatarUrl: Optional[str] = None
    sessionsCompleted: int = 0
    nextSession: Optional[NextSessionSnippet] = None


class MenteeDetail(BaseModel):
    id: str
    name: Optional[str] = None
    email: str
    avatarUrl: Optional[str] = None
    bio: Optional[str] = None
    skills: List[str] = []
    goals: List[str] = []
    sessions: List[SessionOut] = []


# ── Notifications ──────────────────────────────────────────────────────────────

class NotificationOut(BaseModel):
    id: str
    type: str          # "request" | "session" | "message" | "system"
    title: str
    description: str
    timestamp: str     # human-readable relative time
    read: bool
    createdAt: datetime

    model_config = {"from_attributes": True, "populate_by_name": True}


class NotificationMarkReadIn(BaseModel):
    ids: Optional[List[str]] = None   # None = mark all


# ── Mentor Application (4-Step Form) ───────────────────────────────────────────

class MentorApplyStep1In(BaseModel):
    """Step 1: Personal Information"""
    phone_number: str = Field(..., min_length=10, alias="phoneNumber")
    location: str = Field(..., min_length=2)
    gender: str = Field(..., min_length=1)
    
    model_config = {"populate_by_name": True}


class MentorApplyStep2In(BaseModel):
    """Step 2: Professional Background"""
    job_title: str = Field(..., min_length=1, alias="jobTitle")
    company: Optional[str] = Field(None, min_length=1)
    years_experience: int = Field(..., ge=0, alias="yearsExperience")
    linkedin_url: Optional[str] = Field(None, alias="linkedinUrl")
    skills: List[str] = Field(..., min_items=1)  # List of skill strings
    professional_bio: str = Field(..., min_length=50, alias="professionalBio")
    
    model_config = {"populate_by_name": True}


class MentorApplyStep3In(BaseModel):
    """Step 3: Document Upload"""
    id_document_url: str = Field(..., alias="idDocumentUrl")
    id_document_type: str = Field(..., alias="idDocumentType")  # "nin" | "passport" | "driver_license"
    professional_certificate_url: str = Field(..., alias="professionalCertificateUrl")
    
    model_config = {"populate_by_name": True}
    
    @field_validator("id_document_type")
    @classmethod
    def validate_doc_type(cls, v: str) -> str:
        valid_types = {"nin", "passport", "driver_license"}
        if v.lower() not in valid_types:
            raise ValueError(f"id_document_type must be one of {valid_types}")
        return v.lower()


class MentorApplyStep4In(BaseModel):
    """Step 4: Review and Submit (just triggers submission, no new data)"""
    pass


class MentorApplicationStep1Out(BaseModel):
    """Response after completing Step 1"""
    id: str
    mentorId: str = Field(alias="mentorId")
    phoneNumber: str = Field(alias="phoneNumber")
    location: str
    gender: str
    step1Completed: bool = Field(alias="step1Completed")
    status: str
    
    model_config = {"from_attributes": True, "populate_by_name": True}


class MentorApplicationStep2Out(BaseModel):
    """Response after completing Step 2"""
    id: str
    mentorId: str = Field(alias="mentorId")
    jobTitle: str = Field(alias="jobTitle")
    company: Optional[str] = None
    yearsExperience: int = Field(alias="yearsExperience")
    linkedinUrl: Optional[str] = Field(alias="linkedinUrl")
    skills: List[str] = []
    professionalBio: str = Field(alias="professionalBio")
    step2Completed: bool = Field(alias="step2Completed")
    status: str
    
    model_config = {"from_attributes": True, "populate_by_name": True}
    
    @field_validator("skills", mode="before")
    @classmethod
    def parse_skills(cls, v):
        return _split(v) if isinstance(v, str) else (v or [])


class MentorApplicationStep3Out(BaseModel):
    """Response after completing Step 3"""
    id: str
    mentorId: str = Field(alias="mentorId")
    idDocumentUrl: str = Field(alias="idDocumentUrl")
    idDocumentType: str = Field(alias="idDocumentType")
    professionalCertificateUrl: str = Field(alias="professionalCertificateUrl")
    step3Completed: bool = Field(alias="step3Completed")
    status: str
    
    model_config = {"from_attributes": True, "populate_by_name": True}


class MentorApplicationReviewOut(BaseModel):
    """Step 4: Full application summary for review"""
    id: str
    mentorId: str = Field(alias="mentorId")
    
    # Step 1
    phoneNumber: str = Field(alias="phoneNumber")
    location: str
    gender: str
    step1Completed: bool = Field(alias="step1Completed")
    
    # Step 2
    jobTitle: str = Field(alias="jobTitle")
    company: Optional[str] = None
    yearsExperience: int = Field(alias="yearsExperience")
    linkedinUrl: Optional[str] = Field(alias="linkedinUrl")
    skills: List[str] = []
    professionalBio: str = Field(alias="professionalBio")
    step2Completed: bool = Field(alias="step2Completed")
    
    # Step 3
    idDocumentUrl: str = Field(alias="idDocumentUrl")
    idDocumentType: str = Field(alias="idDocumentType")
    professionalCertificateUrl: str = Field(alias="professionalCertificateUrl")
    step3Completed: bool = Field(alias="step3Completed")
    
    # Status
    status: str
    createdAt: datetime = Field(alias="createdAt")
    updatedAt: datetime = Field(alias="updatedAt")
    
    model_config = {"from_attributes": True, "populate_by_name": True}
    
    @field_validator("skills", mode="before")
    @classmethod
    def parse_skills(cls, v):
        return _split(v) if isinstance(v, str) else (v or [])


class MentorApplicationStatusOut(BaseModel):
    """Current application status"""
    id: str
    mentorId: str = Field(alias="mentorId")
    status: str
    step1Completed: bool = Field(alias="step1Completed")
    step2Completed: bool = Field(alias="step2Completed")
    step3Completed: bool = Field(alias="step3Completed")
    submittedAt: Optional[datetime] = Field(None, alias="submittedAt")
    createdAt: datetime = Field(alias="createdAt")
    
    model_config = {"from_attributes": True, "populate_by_name": True}