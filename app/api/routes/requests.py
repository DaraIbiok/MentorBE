"""
Mentorship request routes.

POST   /api/requests                        – mentee creates request
GET    /api/mentor/requests                 – mentor lists their requests
PATCH  /api/mentor/requests/:requestId      – mentor accepts / declines

When a request is ACCEPTED:
  1. A Session is auto-created (scheduled 7 days from now as a placeholder).
  2. A notification is sent to the mentee: "Your request was accepted".
  3. A notification is sent to the mentor: "You have a new mentee".

When a request is DECLINED:
  1. A notification is sent to the mentee: "Your request was declined".
"""

import uuid
from datetime import datetime, timedelta
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.auth import get_current_user, require_mentee, require_mentor
from app.db.database import get_db
from app.models.models import MentorshipRequest, Notification, Session as SessionModel, User
from app.schemas.schemas import (
    MenteeSnippet,
    MentorshipRequestIn,
    MentorshipRequestOut,
    MentorshipRequestStatusIn,
    UserSnippet,
)

mentee_router = APIRouter(prefix="/api/requests", tags=["requests"])
mentor_router = APIRouter(prefix="/api/mentor/requests", tags=["mentor-requests"])


def _uuid():
    return str(uuid.uuid4())


# ── helpers ────────────────────────────────────────────────────────────────────

def _to_out(req):
    return MentorshipRequestOut(
        id=req.id,
        menteeId=req.mentee_id,
        mentorId=req.mentor_id,
        topic=req.topic,
        message=req.message,
        status=req.status,
        createdAt=req.created_at,
        mentee=UserSnippet(id=req.mentee.id, name=req.mentee.name, avatarUrl=req.mentee.avatar_url),
        mentor=UserSnippet(id=req.mentor.id, name=req.mentor.name, avatarUrl=req.mentor.avatar_url),
    )

def _create_notification(
    db: Session,
    user_id: str,
    type_: str,
    title: str,
    description: str,
    related_id: str | None = None,
):
    n = Notification(
        id=_uuid(),
        user_id=user_id,
        type=type_,
        title=title,
        description=description,
        related_id=related_id,
    )
    db.add(n)


# ── Mentee ─────────────────────────────────────────────────────────────────────

@mentee_router.post("", response_model=MentorshipRequestOut, status_code=201)
def create_request(
    body: MentorshipRequestIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_mentee),
):
    """Mentee submits a mentorship request to a mentor."""
    mentor = db.query(User).filter(User.id == body.mentor_id, User.role == "mentor").first()
    if not mentor:
        raise HTTPException(status_code=404, detail="Mentor not found")

    req = MentorshipRequest(
        id=_uuid(),
        mentee_id=current_user.id,
        mentor_id=body.mentor_id,
        topic=body.topic,
        message=body.message,
        preferred_time=body.preferred_time,
    )
    db.add(req)

    # Notify mentor about the new request
    _create_notification(
        db,
        user_id=mentor.id,
        type_="request",
        title="New mentorship request",
        description=f"{current_user.name} wants to connect with you — \"{body.topic}\"",
        related_id=req.id,
    )

    db.commit()
    db.refresh(req)
    return _to_out(req)


# ── Mentor ─────────────────────────────────────────────────────────────────────

@mentor_router.get("", response_model=List[MentorshipRequestOut])
def list_mentor_requests(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_mentor),
):
    """Return all requests sent to the current mentor, newest first."""
    requests = (
        db.query(MentorshipRequest)
        .filter(MentorshipRequest.mentor_id == current_user.id)
        .order_by(MentorshipRequest.created_at.desc())
        .all()
    )
    return [_to_out(r) for r in requests]


@mentor_router.patch("/{request_id}", response_model=MentorshipRequestOut)
def respond_to_request(
    request_id: str,
    body: MentorshipRequestStatusIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_mentor),
):
    """
    Mentor accepts or declines a pending request.

    On ACCEPT:
      - Session is auto-created (placeholder: 7 days from now, 60 min).
      - Mentee gets notified: request accepted + session scheduled.
      - Mentor gets notified: new mentee added.

    On DECLINE:
      - Mentee gets notified: request declined.
    """
    if body.status not in ("accepted", "declined"):
        raise HTTPException(status_code=400, detail="status must be 'accepted' or 'declined'")

    req = (
        db.query(MentorshipRequest)
        .filter(
            MentorshipRequest.id == request_id,
            MentorshipRequest.mentor_id == current_user.id,
        )
        .first()
    )
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
    if req.status != "pending":
        raise HTTPException(status_code=409, detail="Request already responded to")

    req.status = body.status

    if body.status == "accepted":
        # ── Auto-create a placeholder session ────────────────────────────────
        # Scheduled 7 days from now; mentee/mentor can reschedule from the app.
        placeholder_time = req.preferred_time or (datetime.utcnow() + timedelta(days=7))

        session = SessionModel(
            id=_uuid(),
            mentor_id=current_user.id,
            mentee_id=req.mentee_id,
            topic=req.topic,
            scheduled_at=placeholder_time,
            duration_minutes=60,
            status="scheduled",
        )
        db.add(session)

        # Notify the mentee
        _create_notification(
            db,
            user_id=req.mentee_id,
            type_="request",
            title="Mentorship request accepted! 🎉",
            description=(
                f"{current_user.name} accepted your request for \"{req.topic}\". "
                f"A session has been scheduled."
            ),
            related_id=session.id,
        )

        # Notify the mentor (confirmation)
        _create_notification(
            db,
            user_id=current_user.id,
            type_="session",
            title="New session scheduled",
            description=(
                f"You accepted {req.mentee.name}'s request. "
                f"Session \"{req.topic}\" has been added to your schedule."
            ),
            related_id=session.id,
        )

    elif body.status == "declined":
        # Notify the mentee
        _create_notification(
            db,
            user_id=req.mentee_id,
            type_="request",
            title="Mentorship request declined",
            description=(
                f"{current_user.name} is unable to take on your request "
                f"for \"{req.topic}\" at this time."
            ),
            related_id=req.id,
        )

    db.commit()
    db.refresh(req)
    return _to_out(req)
