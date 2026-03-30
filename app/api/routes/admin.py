"""
Admin routes — user management, session oversight, platform stats.
All routes require role == "admin".
"""

from typing import List, Optional
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.auth import require_admin
from app.db.database import get_db
from app.models.models import Notification, Rating, Session as SessionModel, User
from app.schemas.schemas import SessionOut, UserSnippet
from app.api.routes.profile import _user_response
import uuid

router = APIRouter(prefix="/api/admin", tags=["admin"])


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


# ── Stats ──────────────────────────────────────────────────────────────────────

@router.get("/stats")
def get_stats(
    request: Request,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    total_users = db.query(func.count(User.id)).scalar() or 0
    total_mentors = db.query(func.count(User.id)).filter(User.role == "mentor").scalar() or 0
    total_mentees = db.query(func.count(User.id)).filter(User.role == "mentee").scalar() or 0
    total_sessions = db.query(func.count(SessionModel.id)).scalar() or 0
    active_sessions = db.query(func.count(SessionModel.id)).filter(
        SessionModel.status.in_(["scheduled", "in_progress"])
    ).scalar() or 0
    completed_sessions = db.query(func.count(SessionModel.id)).filter(
        SessionModel.status == "completed"
    ).scalar() or 0
    pending_mentors = db.query(func.count(User.id)).filter(
        User.role == "mentor", User.verification_status == "pending"
    ).scalar() or 0

    six_months_ago = datetime.utcnow() - timedelta(days=180)
    monthly_sessions = (
        db.query(
            func.date_format(SessionModel.created_at, "%Y-%m").label("month"),
            func.count(SessionModel.id).label("count"),
        )
        .filter(SessionModel.created_at >= six_months_ago)
        .group_by("month")
        .order_by("month")
        .all()
    )

    recent_users = db.query(User).order_by(User.created_at.desc()).limit(5).all()
    recent_sessions = db.query(SessionModel).order_by(SessionModel.created_at.desc()).limit(5).all()
    base = str(request.base_url)

    return JSONResponse({
        "totalUsers": total_users,
        "totalMentors": total_mentors,
        "totalMentees": total_mentees,
        "totalSessions": total_sessions,
        "activeSessions": active_sessions,
        "completedSessions": completed_sessions,
        "pendingMentors": pending_mentors,
        "monthlySessions": [{"month": r.month, "count": r.count} for r in monthly_sessions],
        "recentUsers": [_user_response(u, base) for u in recent_users],
        "recentSessions": [
            {
                "id": s.id,
                "topic": s.topic,
                "status": s.status,
                "scheduledAt": s.scheduled_at.isoformat() if s.scheduled_at else None,
                "mentor": s.mentor.name,
                "mentee": s.mentee.name,
            }
            for s in recent_sessions
        ],
    })


# ── Users ──────────────────────────────────────────────────────────────────────

@router.get("/users")
def list_users(
    request: Request,
    role: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    q = db.query(User)
    if role:
        q = q.filter(User.role == role)
    users = q.order_by(User.created_at.desc()).all()
    base = str(request.base_url)
    return JSONResponse([_user_response(u, base) for u in users])


@router.patch("/users/{user_id}/deactivate")
def deactivate_user(
    request: Request,
    user_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.is_active = False
    if user.role == "mentor":
        user.verification_status = "rejected"
    db.commit()
    db.refresh(user)
    return JSONResponse(_user_response(user, str(request.base_url)))


@router.patch("/users/{user_id}/activate")
def activate_user(
    request: Request,
    user_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.is_active = True
    if user.role == "mentor":
        user.verification_status = "approved"
    db.commit()
    db.refresh(user)
    return JSONResponse(_user_response(user, str(request.base_url)))


# ── Mentor Verification ────────────────────────────────────────────────────────

@router.patch("/mentors/{user_id}/approve")
def approve_mentor(
    request: Request,
    user_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    """Approve a pending mentor application."""
    mentor = db.query(User).filter(User.id == user_id, User.role == "mentor").first()
    if not mentor:
        raise HTTPException(status_code=404, detail="Mentor not found")
    mentor.verification_status = "approved"
    mentor.is_active = True

    # Notify the mentor
    notif = Notification(
        id=str(uuid.uuid4()),
        user_id=mentor.id,
        type="system",
        title="🎉 Your mentor application was approved!",
        description="Congratulations! Your profile is now live and mentees can find and connect with you.",
    )
    db.add(notif)
    db.commit()
    db.refresh(mentor)
    return JSONResponse(_user_response(mentor, str(request.base_url)))


@router.patch("/mentors/{user_id}/reject")
def reject_mentor(
    request: Request,
    user_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    """Reject a pending mentor application."""
    mentor = db.query(User).filter(User.id == user_id, User.role == "mentor").first()
    if not mentor:
        raise HTTPException(status_code=404, detail="Mentor not found")
    mentor.verification_status = "rejected"
    mentor.is_active = False

    # Notify the mentor
    notif = Notification(
        id=str(uuid.uuid4()),
        user_id=mentor.id,
        type="system",
        title="Mentor application update",
        description="Unfortunately your mentor application was not approved at this time. Please update your profile and reapply.",
    )
    db.add(notif)
    db.commit()
    db.refresh(mentor)
    return JSONResponse(_user_response(mentor, str(request.base_url)))


# ── Sessions ──────────────────────────────────────────────────────────────────

@router.get("/sessions", response_model=List[SessionOut])
def list_all_sessions(
    status: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    q = db.query(SessionModel)
    if status:
        q = q.filter(SessionModel.status == status)
    sessions = q.order_by(SessionModel.scheduled_at.desc()).all()
    return [_session_out(s) for s in sessions]