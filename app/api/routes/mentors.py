from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.auth import get_current_user, require_mentee
from app.db.database import get_db
from app.models.models import Rating, User
from app.schemas.schemas import MentorOut, RatingOut, UserSnippet

router = APIRouter(prefix="/api/mentors", tags=["mentors"])


def _build_mentor_out(user: User, avg: float | None, count: int, match_score: int = 0) -> MentorOut:
    skills = [s.strip() for s in user.skills.split(",")] if user.skills else []
    return MentorOut(
        id=user.id,
        name=user.name,
        email=user.email,
        avatarUrl=user.avatar_url,
        bio=user.bio,
        skills=skills,
        averageRating=round(avg, 2) if avg else None,
        ratingCount=count,
        matchScore=match_score,
    )


def _rating_stats(db: Session) -> dict[str, tuple[float, int]]:
    rows = (
        db.query(
            Rating.rated_user_id,
            func.avg(Rating.rating).label("avg"),
            func.count(Rating.id).label("cnt"),
        )
        .group_by(Rating.rated_user_id)
        .all()
    )
    return {r.rated_user_id: (float(r.avg), r.cnt) for r in rows}


def _match_score(mentee: User, mentor: User) -> int:
    mentee_interests = set(
        s.strip().lower()
        for s in ((mentee.skills or "") + "," + (mentee.goals or "")).split(",")
        if s.strip()
    )
    mentor_skills = set(
        s.strip().lower()
        for s in (mentor.skills or "").split(",")
        if s.strip()
    )
    return len(mentee_interests & mentor_skills)


def _approved_mentors(db: Session):
    """Only return mentors who have been verified/approved."""
    return (
        db.query(User)
        .filter(
            User.role == "mentor",
            User.is_active == True,
            User.verification_status == "approved",
        )
        .all()
    )


@router.get("", response_model=List[MentorOut])
def list_mentors(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    mentors = _approved_mentors(db)
    stats = _rating_stats(db)
    result = [_build_mentor_out(m, *stats.get(m.id, (None, 0))) for m in mentors]
    result.sort(key=lambda x: (x.averageRating or 0, x.ratingCount), reverse=True)
    return result


@router.get("/recommended", response_model=List[MentorOut])
def recommended_mentors(db: Session = Depends(get_db), current_user: User = Depends(require_mentee)):
    mentors = _approved_mentors(db)
    stats = _rating_stats(db)
    scored = []
    for m in mentors:
        avg, cnt = stats.get(m.id, (None, 0))
        score = _match_score(current_user, m)
        scored.append((_build_mentor_out(m, avg, cnt, score), score))
    scored.sort(key=lambda x: (x[1], x[0].averageRating or 0, x[0].ratingCount), reverse=True)
    return [item[0] for item in scored]


@router.get("/{mentor_id}", response_model=MentorOut)
def get_mentor(mentor_id: str, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    from fastapi import HTTPException
    mentor = db.query(User).filter(User.id == mentor_id, User.role == "mentor").first()
    if not mentor:
        raise HTTPException(status_code=404, detail="Mentor not found")
    stats = _rating_stats(db)
    avg, cnt = stats.get(mentor.id, (None, 0))
    return _build_mentor_out(mentor, avg, cnt)


@router.get("/{mentor_id}/ratings", response_model=List[RatingOut])
def get_mentor_ratings(mentor_id: str, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    ratings = (
        db.query(Rating)
        .filter(Rating.rated_user_id == mentor_id)
        .order_by(Rating.created_at.desc())
        .all()
    )
    result = []
    for r in ratings:
        tags = [t.strip() for t in r.tags.split(",")] if r.tags else []
        result.append(
            RatingOut(
                id=r.id,
                rating=r.rating,
                comment=r.comment,
                tags=tags,
                createdAt=r.created_at,
                rater=UserSnippet(id=r.rater.id, name=r.rater.name, avatarUrl=r.rater.avatar_url),
            )
        )
    return result