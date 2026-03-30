from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.auth import get_current_user, _decode_token
from app.db.database import get_db
from app.models.models import User
from app.api.routes.profile import _user_response
import uuid

router = APIRouter(tags=["auth"])
bearer_scheme = HTTPBearer()


async def _me(request: Request, current_user: User = Depends(get_current_user)):
    return JSONResponse(_user_response(current_user, str(request.base_url)))


router.add_api_route("/api/auth/me", _me, methods=["GET"])
router.add_api_route("/api/users/me", _me, methods=["GET"])


class RegisterBody(BaseModel):
    email: str
    full_name: str
    role: str = "mentee"


@router.post("/api/auth/register", status_code=201)
async def register(
    request: Request,
    body: RegisterBody,
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
):
    payload = await _decode_token(credentials.credentials)
    sub: str = payload.get("sub", "")
    if not sub:
        raise HTTPException(status_code=401, detail="Token missing sub claim")

    role = body.role if body.role in ("mentee", "mentor") else "mentee"
    user = db.query(User).filter(User.supabase_id == sub).first()

    # Mentors start as pending verification, not active
    is_mentor = role == "mentor"

    if user:
        user.name = body.full_name or user.name
        user.role = role
        if is_mentor and user.verification_status == "not_required":
            user.verification_status = "pending"
            user.is_active = False
        db.commit()
        db.refresh(user)
    else:
        user = User(
            id=str(uuid.uuid4()),
            supabase_id=sub,
            email=body.email,
            name=body.full_name,
            role=role,
            verification_status="pending" if is_mentor else "not_required",
            is_active=not is_mentor,  # mentors start inactive until approved
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    return JSONResponse(
        _user_response(user, str(request.base_url)),
        status_code=201,
    )