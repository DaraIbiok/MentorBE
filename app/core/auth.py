"""
Authentication — supports ES256 (new Supabase) and HS256 (legacy).

SSL Configuration:
------------------
For LOCAL DEV (if certifi causes SSL issues on your network):
  Comment out the certifi line and uncomment verify=False

For PRODUCTION (correct approach):
  Use certifi — pip install --upgrade certifi
  Make sure the certifi line is active and verify=False is commented out
"""

from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.database import get_db
from app.models.models import User

bearer_scheme = HTTPBearer()
_jwks_cache: Optional[dict] = None
_jwks_failed: bool = False


async def _get_jwks() -> Optional[dict]:
    global _jwks_cache, _jwks_failed
    if _jwks_cache is not None:
        return _jwks_cache
    if _jwks_failed:
        return None
    if not settings.SUPABASE_URL:
        return None
    try:
        import httpx
        import certifi
        jwks_url = f"{settings.SUPABASE_URL}/auth/v1/.well-known/jwks.json"
        async with httpx.AsyncClient(
            # ── PRODUCTION: proper SSL verification via certifi ──────────────
            # verify=certifi.where(),          # ← keep this for production
            # ── LOCAL DEV: comment the line above and uncomment below ────────
            verify=False,                  # ← use this if SSL errors locally
            timeout=5,
        ) as client:
            resp = await client.get(jwks_url)
            resp.raise_for_status()
            _jwks_cache = resp.json()
            return _jwks_cache
    except Exception as e:
        print(f"[auth] JWKS fetch failed ({e}). Falling back to HS256.")
        _jwks_failed = True
        return None


async def _decode_token_es256(token: str) -> Optional[dict]:
    jwks = await _get_jwks()
    if not jwks:
        return None
    try:
        from jose import jwk as jose_jwk
        header = jwt.get_unverified_header(token)
        kid = header.get("kid")
        key_data = next(
            (k for k in jwks.get("keys", []) if kid is None or k.get("kid") == kid),
            None,
        )
        if key_data is None:
            return None
        public_key = jose_jwk.construct(key_data)
        return jwt.decode(token, public_key, algorithms=["ES256"], options={"verify_aud": False})
    except Exception:
        return None


def _decode_token_hs256(token: str) -> Optional[dict]:
    if not settings.SUPABASE_JWT_SECRET:
        return None
    try:
        return jwt.decode(
            token,
            settings.SUPABASE_JWT_SECRET,
            algorithms=["HS256"],
            options={"verify_aud": False},
        )
    except Exception:
        return None


async def _decode_token(token: str) -> dict:
    try:
        header = jwt.get_unverified_header(token)
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Malformed token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    alg = header.get("alg", "HS256")
    payload: Optional[dict] = None

    if alg == "ES256":
        # Try ES256 first (new Supabase projects)
        payload = await _decode_token_es256(token)
        # Fall back to HS256 if ES256 fails
        if payload is None:
            payload = _decode_token_hs256(token)
    else:
        # Try HS256 first (legacy Supabase projects)
        payload = _decode_token_hs256(token)
        # Fall back to ES256 if HS256 fails
        if payload is None:
            payload = await _decode_token_es256(token)

    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token verification failed",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return payload


def _get_or_create_user(payload: dict, db: Session) -> User:
    sub: str = payload.get("sub", "")
    if not sub:
        raise HTTPException(status_code=401, detail="Token missing sub claim")

    user = db.query(User).filter(User.supabase_id == sub).first()
    email: str = payload.get("email", "")
    meta: dict = payload.get("user_metadata", {})
    app_meta: dict = payload.get("app_metadata", {})
    role_from_jwt: Optional[str] = meta.get("role") or app_meta.get("role")
    name_from_jwt: str = (
        meta.get("name") or meta.get("full_name") or email.split("@")[0]
    )

    if user is None:
        is_mentor = role_from_jwt == "mentor"
        user = User(
            supabase_id=sub,
            email=email,
            name=name_from_jwt,
            role=role_from_jwt if role_from_jwt in ("mentee", "mentor", "admin") else "mentee",
            verification_status="pending" if is_mentor else "not_required",
            is_active=not is_mentor,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    else:
        changed = False
        if email and user.email != email:
            user.email = email
            changed = True
        # Only sync role from JWT if user has no role yet (don't overwrite manually set roles)
        # if role_from_jwt and role_from_jwt in ("mentee", "mentor", "admin") and not user.role:
        #     user.role = role_from_jwt
        #     changed = True
        if changed:
            db.commit()
            db.refresh(user)
    return user


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    payload = await _decode_token(credentials.credentials)
    return _get_or_create_user(payload, db)


async def require_mentee(user: User = Depends(get_current_user)) -> User:
    if user.role != "mentee":
        raise HTTPException(status_code=403, detail="Mentee access only")
    return user


async def require_mentor(user: User = Depends(get_current_user)) -> User:
    if user.role != "mentor":
        raise HTTPException(status_code=403, detail="Mentor access only")
    return user


async def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access only")
    return user