"""
Mentor → mentee management routes.

GET  /api/mentor/mentees           – all mentees (sessions + accepted requests)
GET  /api/mentor/mentees/:menteeId – single mentee detail + sessions
"""

from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.auth import require_mentor
from app.db.database import get_db
from app.models.models import MentorshipRequest, Session as SessionModel, User
from app.schemas.schemas import (
    MenteeDetail,
    MenteeListItem,
    NextSessionSnippet,
    SessionOut,
    UserSnippet,
)

router = APIRouter(prefix="/api/mentor/mentees", tags=["mentor-mentees"])


def _session_out(s: SessionModel) -> SessionOut:
    return SessionOut(
        id=s.id,
        mentorId=s.mentor_id,
        menteeId=s.mentee_id,
        topic=s.topic,
        scheduledAt=s.scheduled_at,
        durationMinutes=s.duration_minutes,
        status=s.status,
        videoRoomUrl=s.video_room_url,
        mentor=UserSnippet(id=s.mentor.id, name=s.mentor.name, avatarUrl=s.mentor.avatar_url),
        mentee=UserSnippet(id=s.mentee.id, name=s.mentee.name, avatarUrl=s.mentee.avatar_url),
    )


@router.get("", response_model=List[MenteeListItem])
def list_mentees(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_mentor),
):
    """
    Return all distinct mentees for this mentor.
    Includes mentees with accepted requests even if no sessions exist yet.
    """
    now = datetime.utcnow()

    sessions = (
        db.query(SessionModel)
        .filter(SessionModel.mentor_id == current_user.id)
        .order_by(SessionModel.scheduled_at.asc())
        .all()
    )

    accepted_requests = (
        db.query(MentorshipRequest)
        .filter(
            MentorshipRequest.mentor_id == current_user.id,
            MentorshipRequest.status == "accepted",
        )
        .all()
    )

    mentee_map: dict[str, dict] = {}

    for req in accepted_requests:
        mid = req.mentee_id
        if mid not in mentee_map:
            mentee_map[mid] = {"user": req.mentee, "completed": 0, "next_session": None}

    for s in sessions:
        mid = s.mentee_id
        if mid not in mentee_map:
            mentee_map[mid] = {"user": s.mentee, "completed": 0, "next_session": None}
        if s.status == "completed":
            mentee_map[mid]["completed"] += 1
        if (
            s.status == "scheduled"
            and s.scheduled_at >= now
            and mentee_map[mid]["next_session"] is None
        ):
            mentee_map[mid]["next_session"] = s

    result = []
    for data in mentee_map.values():
        u: User = data["user"]
        ns = data["next_session"]
        result.append(
            MenteeListItem(
                id=u.id,
                name=u.name,
                avatarUrl=u.avatar_url,
                sessionsCompleted=data["completed"],
                nextSession=NextSessionSnippet(
                    id=ns.id,
                    topic=ns.topic,
                    scheduledAt=ns.scheduled_at,
                    durationMinutes=ns.duration_minutes,
                ) if ns else None,
            )
        )
    return result


@router.get("/{mentee_id}", response_model=MenteeDetail)
def get_mentee(
    mentee_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_mentor),
):
    """Return a single mentee's profile and all shared sessions."""
    has_relationship = (
        db.query(MentorshipRequest)
        .filter(
            MentorshipRequest.mentor_id == current_user.id,
            MentorshipRequest.mentee_id == mentee_id,
            MentorshipRequest.status == "accepted",
        )
        .first()
    )

    mentee = db.query(User).filter(User.id == mentee_id, User.role == "mentee").first()
    if not mentee:
        raise HTTPException(status_code=404, detail="Mentee not found")
    if not has_relationship:
        raise HTTPException(status_code=403, detail="No accepted relationship with this mentee")

    sessions = (
        db.query(SessionModel)
        .filter(
            SessionModel.mentor_id == current_user.id,
            SessionModel.mentee_id == mentee_id,
        )
        .order_by(SessionModel.scheduled_at.desc())
        .all()
    )

    skills = [s.strip() for s in mentee.skills.split(",")] if mentee.skills else []
    goals = [g.strip() for g in mentee.goals.split(",")] if mentee.goals else []

    return MenteeDetail(
        id=mentee.id,
        name=mentee.name,
        email=mentee.email,
        avatarUrl=mentee.avatar_url,
        bio=mentee.bio,
        skills=skills,
        goals=goals,
        sessions=[_session_out(s) for s in sessions],
    )
