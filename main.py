import os
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import settings
from app.db.database import Base, engine
from app.api.routes import auth, profile, mentors, sessions, admin
from app.api.routes.requests import mentee_router, mentor_router
from app.api.routes.mentor_mentees import router as mentees_router
from app.api.routes.notifications import router as notifications_router
from app.api.routes.mentor_application import router as mentor_application_router

Base.metadata.create_all(bind=engine)

app = FastAPI(title="MentorMe API", version="1.0.0")

# ── CORS for API routes ────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["settings.origins_list", "https://mentor-fe-sigma.vercel.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# ── CORS for static files (uploads) ───────────────────────────────────────────
class StaticFilesCORSMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        if request.url.path.startswith("/uploads/"):
            response.headers["Access-Control-Allow-Origin"] = "*"
            response.headers["Cache-Control"] = "no-cache"
        return response

app.add_middleware(StaticFilesCORSMiddleware)

# ── Static file serving ───────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / settings.UPLOAD_DIR
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
(UPLOAD_DIR / "avatars").mkdir(exist_ok=True)

app.mount("/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(auth.router)
app.include_router(profile.router)
app.include_router(mentors.router)
app.include_router(sessions.router)
app.include_router(mentee_router)
app.include_router(mentor_router)
app.include_router(mentees_router)
app.include_router(admin.router)
app.include_router(notifications_router)
app.include_router(mentor_application_router)


@app.get("/health", tags=["health"])
def health_check():
    return {"status": "ok", "env": settings.APP_ENV}


#time on the notifications
#testing the video call thing, what if the user doesn't want a video call
#avatar, rating, admin dashboard
#mentor verification, goal tracking
#- Camera icon on the avatar in Settings → click → pick image → instant preview → uploads to backend → URL saved → avatar updates everywhere including the nav
#emial notifications for session reminders, new messages, etc. (using a background task or external service)
#messaging