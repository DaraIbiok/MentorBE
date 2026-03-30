# Mentor Application Form - 4-Step Implementation

## Overview
This document describes the four-step mentor application form that appears after a mentor completes basic registration (email verification).

## Database Schema

### MentorApplication Table
```sql
CREATE TABLE mentor_applications (
    id STRING PRIMARY KEY,
    mentor_id STRING UNIQUE NOT NULL,
    
    -- Step 1: Personal Information
    phone_number STRING(20),
    location STRING(255),
    gender STRING(50),
    step_1_completed BOOLEAN DEFAULT FALSE,
    
    -- Step 2: Professional Background
    job_title STRING(255),
    company STRING(255),
    years_experience INTEGER,
    linkedin_url STRING(512),
    skills TEXT (comma-separated),
    professional_bio TEXT,
    step_2_completed BOOLEAN DEFAULT FALSE,
    
    -- Step 3: Document Upload
    id_document_url STRING(512),
    id_document_type STRING(50),  -- "nin", "passport", "driver_license"
    professional_certificate_url STRING(512),
    step_3_completed BOOLEAN DEFAULT FALSE,
    
    -- Step 4: Review and Submit
    submitted_at DATETIME,
    status ENUM('draft', 'step_1', 'step_2', 'step_3', 'review', 'submitted', 'approved', 'rejected'),
    
    -- Admin Review
    admin_notes TEXT,
    reviewed_at DATETIME,
    reviewed_by STRING(36) FK users.id,
    
    created_at DATETIME,
    updated_at DATETIME
);
```

## API Endpoints

### Step 1: Personal Information
**POST** `/api/mentor/apply/step1`

Request:
```json
{
  "phoneNumber": "+2348123456789",
  "location": "Lagos, Nigeria",
  "gender": "Male"
}
```

Response:
```json
{
  "id": "app-uuid",
  "mentorId": "user-uuid",
  "phoneNumber": "+2348123456789",
  "location": "Lagos, Nigeria",
  "gender": "Male",
  "step1Completed": true,
  "status": "step_1"
}
```

HTTP Errors:
- `403` - Only mentor accounts can apply
- `400` - Already submitted or invalid data

---

### Step 2: Professional Background
**POST** `/api/mentor/apply/step2`

Request:
```json
{
  "jobTitle": "Senior Software Engineer",
  "company": "Tech Corp Ltd",
  "yearsExperience": 8,
  "linkedinUrl": "https://linkedin.com/in/johndoe",
  "skills": ["Python", "Django", "FastAPI", "Machine Learning", "System Design"],
  "professionalBio": "Experienced software engineer with 8 years in full-stack development. Passionate about mentoring junior developers and sharing knowledge on system design and best practices."
}
```

Response:
```json
{
  "id": "app-uuid",
  "mentorId": "user-uuid",
  "jobTitle": "Senior Software Engineer",
  "company": "Tech Corp Ltd",
  "yearsExperience": 8,
  "linkedinUrl": "https://linkedin.com/in/johndoe",
  "skills": ["Python", "Django", "FastAPI", "Machine Learning", "System Design"],
  "professionalBio": "Experienced software engineer...",
  "step2Completed": true,
  "status": "step_2"
}
```

Validation:
- `jobTitle`: Required, min 1 character
- `yearsExperience`: Required, >= 0
- `skills`: Required array with at least 1 item
- `professionalBio`: Required, min 50 characters
- `linkedinUrl`: Optional

HTTP Errors:
- `403` - Only mentor accounts can apply
- `400` - Step 1 not completed, already submitted, or invalid data

---

### Step 3: Document Upload

#### 3a. Upload Documents
**POST** `/api/profile/upload-doc`

This endpoint should be called twice:
1. First upload for ID document
2. Second upload for professional certificate

Query Parameters:
- `subfolder`: `"verification"` (default)

Request (multipart/form-data):
```
file: <binary file>
```

Response:
```json
{
  "url": "/uploads/verification/abc123def456.pdf",
  "message": "Document uploaded successfully"
}
```

Constraints:
- Accepted formats: `.pdf`, `.jpg`, `.jpeg`, `.png`
- Max file size: 5MB

HTTP Errors:
- `400` - Invalid file type
- `413` - File too large

#### 3b. Save Document URLs
**POST** `/api/mentor/apply/step3`

Request:
```json
{
  "idDocumentUrl": "/uploads/verification/abc123.pdf",
  "idDocumentType": "passport",
  "professionalCertificateUrl": "/uploads/verification/def456.pdf"
}
```

Response:
```json
{
  "id": "app-uuid",
  "mentorId": "user-uuid",
  "idDocumentUrl": "/uploads/verification/abc123.pdf",
  "idDocumentType": "passport",
  "professionalCertificateUrl": "/uploads/verification/def456.pdf",
  "step3Completed": true,
  "status": "step_3"
}
```

`idDocumentType` must be one of:
- `"nin"` - National ID Number (NIN)
- `"passport"` - Passport
- `"driver_license"` - Driver's License

HTTP Errors:
- `403` - Only mentor accounts can apply
- `400` - Steps 1 & 2 not completed, already submitted, or invalid idDocumentType

---

### Step 4: Review and Submit

#### 4a. Get Application Summary
**GET** `/api/mentor/application/review`

Response:
```json
{
  "id": "app-uuid",
  "mentorId": "user-uuid",
  "phoneNumber": "+2348123456789",
  "location": "Lagos, Nigeria",
  "gender": "Male",
  "step1Completed": true,
  "jobTitle": "Senior Software Engineer",
  "company": "Tech Corp Ltd",
  "yearsExperience": 8,
  "linkedinUrl": "https://linkedin.com/in/johndoe",
  "skills": ["Python", "Django", "FastAPI", "ML", "System Design"],
  "professionalBio": "...",
  "step2Completed": true,
  "idDocumentUrl": "/uploads/verification/abc123.pdf",
  "idDocumentType": "passport",
  "professionalCertificateUrl": "/uploads/verification/def456.pdf",
  "step3Completed": true,
  "status": "review",
  "createdAt": "2026-03-23T10:00:00Z",
  "updatedAt": "2026-03-23T10:15:00Z"
}
```

HTTP Errors:
- `403` - Only mentor accounts can apply
- `400` - Not all steps completed

#### 4b. Final Submission
**POST** `/api/mentor/apply/step4`

Request:
```json
{}
```

Response:
```json
{
  "message": "Application submitted successfully. Please wait for admin review.",
  "application": { ... }  // Full application object
}
```

**Side Effects:**
- Application status → `"submitted"`
- User `verification_status` → `"pending"`
- User `is_active` → `false` (until approved)
- User bio/skills updated from application

HTTP Errors:
- `403` - Only mentor accounts can apply
- `400` - Already submitted or not all steps completed

---

## Status Endpoints

### Get Application Status
**GET** `/api/mentor/application`

Response:
```json
{
  "id": "app-uuid",
  "mentorId": "user-uuid",
  "status": "step_2",
  "step1Completed": true,
  "step2Completed": false,
  "step3Completed": false,
  "submittedAt": null,
  "createdAt": "2026-03-23T10:00:00Z"
}
```

## Frontend Flow

```
1. Mentor completes basic registration (email, password)
2. Redirected to /mentor/apply/step1
3. Fills personal info → POST /api/mentor/apply/step1
4. Redirected to /mentor/apply/step2
5. Fills professional background → POST /api/mentor/apply/step2
6. Redirected to /mentor/apply/step3
7. Uploads ID document → POST /api/profile/upload-doc
8. Uploads professional certificate → POST /api/profile/upload-doc
9. Submits document URLs → POST /api/mentor/apply/step3
10. Redirected to /mentor/apply/review
11. GET /api/mentor/application/review to display summary
12. Confirms and submits → POST /api/mentor/apply/step4
13. Shown "Application submitted. Awaiting admin review" message
14. User account deactivated (is_active = false) until admin approves
15. Admin reviews and approves/rejects
16. On approval: is_active = true, verification_status = "approved"
```

## Admin Review (Future Endpoint)

The admin interface should have an endpoint to review and approve/reject applications:

```
PATCH /api/admin/applications/{applicationId}/review

Request:
{
  "status": "approved" | "rejected",
  "notes": "Brief reason if rejecting"
}
```

This would:
- Update `MentorApplication.status`
- Update `MentorApplication.admin_notes`
- Update `MentorApplication.reviewed_at` and `reviewed_by`
- Update `User.verification_status` and `User.is_active`
```

## Error Handling

All endpoints return proper HTTP status codes:
- `400` - Bad request (invalid data, validation failed, workflow violation)
- `403` - Forbidden (not a mentor, insufficient permissions)
- `413` - Payload too large (file too large)
- `500` - Server error

Common Errors:
1. **"Only mentor accounts can apply"** (403)
   - User tried to apply without mentor role

2. **"Please complete Step X first"** (400)
   - User skipped a step in the workflow

3. **"Application already submitted"** (400)
   - User trying to resubmit after already submitting

4. **"Not all steps completed"** (400)
   - Trying to review/submit before completing all steps

5. **"File type not allowed"** (400)
   - Document upload with unsupported format

6. **"File too large (max 5MB)"** (413)
   - Document file exceeds size limit

## Migration

Run Alembic to create the table:
```bash
alembic upgrade head
```

Migration file: `alembic/versions/0002_mentor_application.py`

## Notes

- Each step saves independently but requires previous steps to be complete
- Skills are stored as comma-separated text in DB but returned as array in API
- Document URLs are relative paths stored in `/uploads/verification/`
- Mentors cannot modify application after submission
- Status progression: `draft` → `step_1` → `step_2` → `step_3` → `review` → `submitted`
- After submission, admin must approve before mentor account is reactivated
