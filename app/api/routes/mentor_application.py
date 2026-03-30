"""
Mentor application routes — 4-step application form for mentor verification.

Endpoints:
  POST /api/mentor/apply/step1      — Personal Information
  POST /api/mentor/apply/step2      — Professional Background
  POST /api/mentor/apply/step3      — Document Upload
  POST /api/mentor/apply/step4      — Review and Submit
  GET  /api/mentor/application      — Get application status
  GET  /api/mentor/application/review — Get full application for review
  POST /api/profile/upload-doc      — Upload verification documents
"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from datetime import datetime
from typing import List

from app.core.auth import get_current_user
from app.db.database import get_db
from app.models.models import User, MentorApplication
from app.schemas.schemas import (
    MentorApplyStep1In,
    MentorApplyStep2In,
    MentorApplyStep3In,
    MentorApplyStep4In,
    MentorApplicationStep1Out,
    MentorApplicationStep2Out,
    MentorApplicationStep3Out,
    MentorApplicationReviewOut,
    MentorApplicationStatusOut,
)
from app.services.upload_service import upload_file

router = APIRouter(tags=["mentor-application"])


def _get_or_create_application(mentor_id: str, db: Session) -> MentorApplication:
    """Get or create a mentor application."""
    app = db.query(MentorApplication).filter(
        MentorApplication.mentor_id == mentor_id
    ).first()
    
    if not app:
        app = MentorApplication(mentor_id=mentor_id, status="draft")
        db.add(app)
        db.commit()
        db.refresh(app)
    
    return app


def _to_camel(snake: str) -> str:
    """Convert snake_case to camelCase."""
    parts = snake.split("_")
    return parts[0] + "".join(p.capitalize() for p in parts[1:])


def _application_to_dict(app: MentorApplication) -> dict:
    """Convert MentorApplication ORM to dict with camelCase keys."""
    data = {
        "id": app.id,
        "mentorId": app.mentor_id,
        "phoneNumber": app.phone_number,
        "location": app.location,
        "gender": app.gender,
        "step1Completed": app.step_1_completed,
        "jobTitle": app.job_title,
        "company": app.company,
        "yearsExperience": app.years_experience,
        "linkedinUrl": app.linkedin_url,
        "skills": [s.strip() for s in (app.skills or "").split(",") if s.strip()],
        "professionalBio": app.professional_bio,
        "step2Completed": app.step_2_completed,
        "idDocumentUrl": app.id_document_url,
        "idDocumentType": app.id_document_type,
        "professionalCertificateUrl": app.professional_certificate_url,
        "step3Completed": app.step_3_completed,
        "status": app.status,
        "submittedAt": app.submitted_at,
        "createdAt": app.created_at,
        "updatedAt": app.updated_at,
    }
    return data


# ── STEP 1: Personal Information ───────────────────────────────────────────────

@router.post("/api/mentor/apply/step1", response_model=MentorApplicationStep1Out)
def submit_step_1(
    body: MentorApplyStep1In,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Step 1: Collect personal information (phone, location, gender).
    Updates application and moves to step_1 status.
    """
    if current_user.role != "mentor":
        raise HTTPException(status_code=403, detail="Only mentor accounts can apply")

    app = _get_or_create_application(current_user.id, db)
    
    # Check if already submitted
    if app.status == "submitted":
        raise HTTPException(status_code=400, detail="Application already submitted")

    # Update Step 1 fields
    app.phone_number = body.phone_number
    app.location = body.location
    app.gender = body.gender
    app.step_1_completed = True
    app.status = "step_1"
    
    db.commit()
    db.refresh(app)
    
    data = _application_to_dict(app)
    return MentorApplicationStep1Out(**data)


# ── STEP 2: Professional Background ────────────────────────────────────────────

@router.post("/api/mentor/apply/step2", response_model=MentorApplicationStep2Out)
def submit_step_2(
    body: MentorApplyStep2In,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Step 2: Collect professional background.
    Requires Step 1 to be completed.
    """
    if current_user.role != "mentor":
        raise HTTPException(status_code=403, detail="Only mentor accounts can apply")

    app = _get_or_create_application(current_user.id, db)
    
    # Check if already submitted
    if app.status == "submitted":
        raise HTTPException(status_code=400, detail="Application already submitted")
    
    # Ensure Step 1 is completed
    if not app.step_1_completed:
        raise HTTPException(status_code=400, detail="Please complete Step 1 first")

    # Update Step 2 fields
    app.job_title = body.job_title
    app.company = body.company
    app.years_experience = body.years_experience
    app.linkedin_url = body.linkedin_url
    app.skills = ",".join(body.skills)  # Store as comma-separated
    app.professional_bio = body.professional_bio
    app.step_2_completed = True
    app.status = "step_2"
    
    db.commit()
    db.refresh(app)
    
    data = _application_to_dict(app)
    return MentorApplicationStep2Out(**data)


# ── STEP 3: Document Upload ───────────────────────────────────────────────────

@router.post("/api/mentor/apply/step3", response_model=MentorApplicationStep3Out)
def submit_step_3(
    body: MentorApplyStep3In,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Step 3: Provide document URLs (already uploaded via separate endpoint).
    Requires Steps 1 & 2 to be completed.
    """
    if current_user.role != "mentor":
        raise HTTPException(status_code=403, detail="Only mentor accounts can apply")

    app = _get_or_create_application(current_user.id, db)
    
    # Check if already submitted
    if app.status == "submitted":
        raise HTTPException(status_code=400, detail="Application already submitted")
    
    # Ensure previous steps are completed
    if not app.step_1_completed:
        raise HTTPException(status_code=400, detail="Please complete Step 1 first")
    if not app.step_2_completed:
        raise HTTPException(status_code=400, detail="Please complete Step 2 first")

    # Update Step 3 fields
    app.id_document_url = body.id_document_url
    app.id_document_type = body.id_document_type
    app.professional_certificate_url = body.professional_certificate_url
    app.step_3_completed = True
    app.status = "step_3"
    
    db.commit()
    db.refresh(app)
    
    data = _application_to_dict(app)
    return MentorApplicationStep3Out(**data)


# ── STEP 4: Review and Submit ──────────────────────────────────────────────────

@router.get("/api/mentor/application/review", response_model=MentorApplicationReviewOut)
def get_application_review(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Step 4: Get full application for final review before submission.
    """
    if current_user.role != "mentor":
        raise HTTPException(status_code=403, detail="Only mentor accounts can apply")

    app = _get_or_create_application(current_user.id, db)
    
    # Check if all steps are completed
    if not (app.step_1_completed and app.step_2_completed and app.step_3_completed):
        raise HTTPException(
            status_code=400,
            detail="Please complete all steps before reviewing"
        )
    
    app.status = "review"
    db.commit()
    db.refresh(app)
    
    data = _application_to_dict(app)
    return MentorApplicationReviewOut(**data)


@router.post("/api/mentor/apply/step4")
def submit_application_final(
    body: MentorApplyStep4In,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Step 4: Final submission. Sets status to 'submitted' and verification_status to 'pending'.
    Admin will review and approve/reject.
    """
    if current_user.role != "mentor":
        raise HTTPException(status_code=403, detail="Only mentor accounts can apply")

    app = _get_or_create_application(current_user.id, db)
    
    # Check if already submitted
    if app.status == "submitted":
        raise HTTPException(status_code=400, detail="Application already submitted")
    
    # Ensure all steps are completed
    if not (app.step_1_completed and app.step_2_completed and app.step_3_completed):
        raise HTTPException(
            status_code=400,
            detail="Please complete all steps before submitting"
        )
    
    # Submit application
    app.status = "submitted"
    app.submitted_at = datetime.utcnow()
    
    # Update user verification status
    current_user.verification_status = "pending"
    current_user.is_active = False  # Deactivate until approved
    
    # Update user's bio and skills from application
    if not current_user.bio:
        current_user.bio = app.professional_bio
    if not current_user.skills:
        current_user.skills = app.skills
    if not current_user.gender:
        current_user.gender = app.gender
    
    db.commit()
    db.refresh(app)
    db.refresh(current_user)
    
    data = _application_to_dict(app)
    return {
        "message": "Application submitted successfully. Please wait for admin review.",
        "application": data,
    }


# ── Status Endpoints ───────────────────────────────────────────────────────────

@router.get("/api/mentor/application", response_model=MentorApplicationStatusOut)
def get_application_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get current application status (all steps)."""
    if current_user.role != "mentor":
        raise HTTPException(status_code=403, detail="Only mentor accounts can apply")

    app = _get_or_create_application(current_user.id, db)
    
    data = _application_to_dict(app)
    return MentorApplicationStatusOut(**data)


# ── Document Upload ────────────────────────────────────────────────────────────

@router.post("/api/profile/upload-doc")
async def upload_document(
    file: UploadFile = File(...),
    subfolder: str = Query("verification"),
    current_user: User = Depends(get_current_user),
):
    """
    Upload a verification document (ID, certificate, etc.).
    Returns the URL to be used in Step 3.
    """
    allowed = {".pdf", ".jpg", ".jpeg", ".png"}
    import os
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in allowed:
        raise HTTPException(status_code=400, detail="Only PDF, JPG, PNG allowed")
    if file.size and file.size > 5 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File too large (max 5MB)")

    url = await upload_file(file, subfolder=subfolder)
    return JSONResponse({"url": url, "message": "Document uploaded successfully"})