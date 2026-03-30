from fastapi import APIRouter, Depends, UploadFile, File, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.db.database import get_db
from app.models.models import User
from app.schemas.schemas import ProfileUpdateIn
from app.services.upload_service import upload_file

router = APIRouter(prefix="/api/profile", tags=["profile"])


def _user_response(user: User, base_url: str) -> dict:
    skills = [s.strip() for s in user.skills.split(",")] if user.skills else []
    goals = [g.strip() for g in user.goals.split(",")] if user.goals else []
    avatar = user.avatar_url or None
    if avatar and not avatar.startswith("http"):
        avatar = f"{base_url.rstrip('/')}{avatar}"
    return {
        "id": user.id,
        "email": user.email,
        "name": user.name,
        "role": user.role,
        "avatarUrl": avatar,
        "bio": user.bio,
        "gender": user.gender,
        "skills": skills,
        "goals": goals,
        "isActive": user.is_active,
        "verificationStatus": getattr(user, "verification_status", "not_required"),
        "createdAt": user.created_at.isoformat() if user.created_at else None,
    }


@router.get("/me")
def get_profile(request: Request, current_user: User = Depends(get_current_user)):
    return JSONResponse(_user_response(current_user, str(request.base_url)))


@router.patch("")
def update_profile(
    request: Request,
    body: ProfileUpdateIn,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if body.name is not None:
        current_user.name = body.name
    if body.avatar_url is not None:
        current_user.avatar_url = body.avatar_url
    if body.bio is not None:
        current_user.bio = body.bio
    if body.gender is not None:
        current_user.gender = body.gender
    if body.skills is not None:
        current_user.skills = ",".join(body.skills)
    if body.goals is not None:
        current_user.goals = ",".join(body.goals)
    if body.role is not None and body.role in ("mentee", "mentor"):
        current_user.role = body.role

    db.commit()
    db.refresh(current_user)
    return JSONResponse(_user_response(current_user, str(request.base_url)))


@router.post("/avatar")
async def upload_avatar(
    request: Request,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    url = await upload_file(file, subfolder="avatars")
    current_user.avatar_url = url
    db.commit()
    db.refresh(current_user)
    return JSONResponse(_user_response(current_user, str(request.base_url)))