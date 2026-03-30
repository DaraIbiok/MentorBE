from typing import List
from datetime import datetime
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.db.database import get_db
from app.models.models import Rating, Session as SessionModel, SessionMessage, User
from app.schemas.schemas import (
    MessageIn, MessageOut, RatingIn, RatingOut,
    SessionCreateIn, SessionDetailOut, SessionOut,
    SessionStatusIn, UserSnippet, VideoRoomOut,
)
from app.services.video_service import get_or_create_room

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


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


def _message_out(m: SessionMessage) -> MessageOut:
    return MessageOut(
        id=m.id,
        sessionId=m.session_id,
        senderId=m.sender_id,
        text=m.text,
        createdAt=m.created_at,
        sender=UserSnippet(id=m.sender.id, name=m.sender.name, avatarUrl=m.sender.avatar_url),
    )


def _get_session_or_404(session_id: str, db: Session) -> SessionModel:
    s = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Session not found")
    return s


def _assert_participant(s: SessionModel, user: User):
    if user.id not in (s.mentor_id, s.mentee_id):
        raise HTTPException(status_code=403, detail="Not a participant of this session")


@router.get("", response_model=List[SessionOut])
def list_sessions(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    sessions = (
        db.query(SessionModel)
        .filter((SessionModel.mentor_id == current_user.id) | (SessionModel.mentee_id == current_user.id))
        .order_by(SessionModel.scheduled_at.desc())
        .all()
    )
    return [_session_out(s) for s in sessions]


@router.get("/{session_id}", response_model=SessionDetailOut)
def get_session(session_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    s = _get_session_or_404(session_id, db)
    _assert_participant(s, current_user)
    return SessionDetailOut(
        **_session_out(s).model_dump(),
        messages=[_message_out(m) for m in s.messages],
    )


@router.post("", response_model=SessionOut, status_code=201)
def create_session(body: SessionCreateIn, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    mentor = db.query(User).filter(User.id == body.mentor_id, User.role == "mentor").first()
    if not mentor:
        raise HTTPException(status_code=404, detail="Mentor not found")
    if current_user.role != "mentee":
        raise HTTPException(status_code=403, detail="Only mentees can create sessions via this endpoint")

    s = SessionModel(
        mentor_id=body.mentor_id,
        mentee_id=current_user.id,
        topic=body.topic,
        scheduled_at=body.scheduled_at,
        duration_minutes=body.duration_minutes,
    )
    db.add(s)
    db.commit()
    db.refresh(s)
    return _session_out(s)


@router.patch("/{session_id}", response_model=SessionOut)
def update_session_status(session_id: str, body: SessionStatusIn, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    allowed = ("scheduled", "in_progress", "completed", "cancelled")
    if body.status not in allowed:
        raise HTTPException(status_code=400, detail=f"status must be one of {allowed}")
    s = _get_session_or_404(session_id, db)
    _assert_participant(s, current_user)
    s.status = body.status
    db.commit()
    db.refresh(s)
    return _session_out(s)


@router.post("/{session_id}/room", response_model=VideoRoomOut)
async def ensure_video_room(session_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    s = _get_session_or_404(session_id, db)
    _assert_participant(s, current_user)
    if s.video_room_url:
        return VideoRoomOut(url=s.video_room_url)
    room = await get_or_create_room(session_id, s.video_room_name)
    s.video_room_url = room["url"]
    s.video_room_name = room["name"]
    db.commit()
    return VideoRoomOut(url=s.video_room_url)


@router.post("/{session_id}/messages", response_model=MessageOut, status_code=201)
def send_message(session_id: str, body: MessageIn, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    s = _get_session_or_404(session_id, db)
    _assert_participant(s, current_user)
    msg = SessionMessage(session_id=session_id, sender_id=current_user.id, text=body.text)
    db.add(msg)
    db.commit()
    db.refresh(msg)
    return _message_out(msg)


@router.get("/{session_id}/ratings", response_model=List[RatingOut])
def list_session_ratings(session_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    s = _get_session_or_404(session_id, db)
    _assert_participant(s, current_user)
    ratings = db.query(Rating).filter(Rating.session_id == session_id).all()
    return [
        RatingOut(
            id=r.id, rating=r.rating, comment=r.comment,
            tags=[t.strip() for t in r.tags.split(",")] if r.tags else [],
            createdAt=r.created_at,
            rater=UserSnippet(id=r.rater.id, name=r.rater.name, avatarUrl=r.rater.avatar_url),
        )
        for r in ratings
    ]


@router.post("/{session_id}/ratings", response_model=RatingOut, status_code=201)
def upsert_rating(session_id: str, body: RatingIn, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    s = _get_session_or_404(session_id, db)
    _assert_participant(s, current_user)
    if s.status != "completed":
        raise HTTPException(status_code=400, detail="Can only rate completed sessions")

    rated_user_id = s.mentor_id if current_user.id == s.mentee_id else s.mentee_id
    existing = db.query(Rating).filter(Rating.session_id == session_id, Rating.rater_id == current_user.id).first()

    if existing:
        existing.rating = body.rating
        existing.comment = body.comment
        existing.tags = ",".join(body.tags)
        db.commit()
        db.refresh(existing)
        r = existing
    else:
        r = Rating(
            session_id=session_id, rater_id=current_user.id,
            rated_user_id=rated_user_id, rating=body.rating,
            comment=body.comment, tags=",".join(body.tags),
        )
        db.add(r)
        db.commit()
        db.refresh(r)

    return RatingOut(
        id=r.id, rating=r.rating, comment=r.comment,
        tags=[t.strip() for t in r.tags.split(",")] if r.tags else [],
        createdAt=r.created_at,
        rater=UserSnippet(id=current_user.id, name=current_user.name, avatarUrl=current_user.avatar_url),
    )


# ── Reschedule session ─────────────────────────────────────────────────────────

class RescheduleIn(BaseModel):
    scheduledAt: datetime
    durationMinutes: int = 60


@router.patch("/{session_id}/reschedule", response_model=SessionOut)
def reschedule_session(
    session_id: str,
    body: RescheduleIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Reschedule a session to a new date/time and duration."""
    s = _get_session_or_404(session_id, db)
    _assert_participant(s, current_user)
    if s.status == "cancelled":
        raise HTTPException(status_code=400, detail="Cannot reschedule a cancelled session")
    s.scheduled_at = body.scheduledAt
    s.duration_minutes = body.durationMinutes
    db.commit()
    db.refresh(s)
    return _session_out(s)
