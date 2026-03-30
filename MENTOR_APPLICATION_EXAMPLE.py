"""
Example workflow for the 4-step mentor application form.
This shows how a frontend should interact with the API.
"""

import requests
import json

BASE_URL = "http://localhost:4000"
MENTOR_TOKEN = "eyJhbGc..."  # JWT token from auth endpoint

headers = {
    "Authorization": f"Bearer {MENTOR_TOKEN}",
    "Content-Type": "application/json"
}


# ──────────────────────────────────────────────────────────────────────────────
# STEP 1: Personal Information
# ──────────────────────────────────────────────────────────────────────────────

print("=" * 80)
print("STEP 1: Personal Information")
print("=" * 80)

step1_data = {
    "phoneNumber": "+2348123456789",
    "location": "Lagos, Nigeria",
    "gender": "Male"
}

response = requests.post(
    f"{BASE_URL}/api/mentor/apply/step1",
    json=step1_data,
    headers=headers
)

print(f"Status: {response.status_code}")
print(f"Response:\n{json.dumps(response.json(), indent=2)}")

# Expected Response:
# {
#   "id": "app-123-uuid",
#   "mentorId": "mentor-456-uuid",
#   "phoneNumber": "+2348123456789",
#   "location": "Lagos, Nigeria",
#   "gender": "Male",
#   "step1Completed": true,
#   "status": "step_1"
# }


# ──────────────────────────────────────────────────────────────────────────────
# STEP 2: Professional Background
# ──────────────────────────────────────────────────────────────────────────────

print("\n" + "=" * 80)
print("STEP 2: Professional Background")
print("=" * 80)

step2_data = {
    "jobTitle": "Senior Software Engineer",
    "company": "Tech Corp Ltd",
    "yearsExperience": 8,
    "linkedinUrl": "https://linkedin.com/in/johndoe",
    "skills": [
        "Python",
        "Django",
        "FastAPI",
        "Machine Learning",
        "System Design",
        "Mentoring"
    ],
    "professionalBio": (
        "Experienced software engineer with 8 years in full-stack development. "
        "Passionate about mentoring junior developers and sharing knowledge on "
        "system design, clean code practices, and scalable architecture. "
        "I help mentees grow from junior to mid-level developers."
    )
}

response = requests.post(
    f"{BASE_URL}/api/mentor/apply/step2",
    json=step2_data,
    headers=headers
)

print(f"Status: {response.status_code}")
print(f"Response:\n{json.dumps(response.json(), indent=2)}")

# Expected Response:
# {
#   "id": "app-123-uuid",
#   "mentorId": "mentor-456-uuid",
#   "jobTitle": "Senior Software Engineer",
#   "company": "Tech Corp Ltd",
#   "yearsExperience": 8,
#   "linkedinUrl": "https://linkedin.com/in/johndoe",
#   "skills": ["Python", "Django", "FastAPI", ...],
#   "professionalBio": "Experienced software engineer...",
#   "step2Completed": true,
#   "status": "step_2"
# }


# ──────────────────────────────────────────────────────────────────────────────
# STEP 3a: Upload Documents
# ──────────────────────────────────────────────────────────────────────────────

print("\n" + "=" * 80)
print("STEP 3a: Upload ID Document")
print("=" * 80)

with open("path/to/passport.pdf", "rb") as f:
    files = {"file": f}
    response = requests.post(
        f"{BASE_URL}/api/profile/upload-doc?subfolder=verification",
        files=files,
        headers={"Authorization": f"Bearer {MENTOR_TOKEN}"}
    )

print(f"Status: {response.status_code}")
id_doc_response = response.json()
print(f"Response:\n{json.dumps(id_doc_response, indent=2)}")

# Expected Response:
# {
#   "url": "/uploads/verification/abc123def456.pdf",
#   "message": "Document uploaded successfully"
# }

id_document_url = id_doc_response["url"]


print("\n" + "=" * 80)
print("STEP 3a: Upload Professional Certificate")
print("=" * 80)

with open("path/to/certificate.pdf", "rb") as f:
    files = {"file": f}
    response = requests.post(
        f"{BASE_URL}/api/profile/upload-doc?subfolder=verification",
        files=files,
        headers={"Authorization": f"Bearer {MENTOR_TOKEN}"}
    )

print(f"Status: {response.status_code}")
cert_response = response.json()
print(f"Response:\n{json.dumps(cert_response, indent=2)}")

certificate_url = cert_response["url"]


# ──────────────────────────────────────────────────────────────────────────────
# STEP 3b: Submit Document URLs
# ──────────────────────────────────────────────────────────────────────────────

print("\n" + "=" * 80)
print("STEP 3b: Submit Document URLs")
print("=" * 80)

step3_data = {
    "idDocumentUrl": id_document_url,
    "idDocumentType": "passport",  # or "nin" or "driver_license"
    "professionalCertificateUrl": certificate_url
}

response = requests.post(
    f"{BASE_URL}/api/mentor/apply/step3",
    json=step3_data,
    headers=headers
)

print(f"Status: {response.status_code}")
print(f"Response:\n{json.dumps(response.json(), indent=2)}")

# Expected Response:
# {
#   "id": "app-123-uuid",
#   "mentorId": "mentor-456-uuid",
#   "idDocumentUrl": "/uploads/verification/abc123def456.pdf",
#   "idDocumentType": "passport",
#   "professionalCertificateUrl": "/uploads/verification/def456ghi789.pdf",
#   "step3Completed": true,
#   "status": "step_3"
# }


# ──────────────────────────────────────────────────────────────────────────────
# STEP 4a: Review Application
# ──────────────────────────────────────────────────────────────────────────────

print("\n" + "=" * 80)
print("STEP 4a: Get Application for Review")
print("=" * 80)

response = requests.get(
    f"{BASE_URL}/api/mentor/application/review",
    headers=headers
)

print(f"Status: {response.status_code}")
review_response = response.json()
print(f"Response:\n{json.dumps(review_response, indent=2)}")

# Expected Response:
# {
#   "id": "app-123-uuid",
#   "mentorId": "mentor-456-uuid",
#   "phoneNumber": "+2348123456789",
#   "location": "Lagos, Nigeria",
#   "gender": "Male",
#   "step1Completed": true,
#   "jobTitle": "Senior Software Engineer",
#   "company": "Tech Corp Ltd",
#   "yearsExperience": 8,
#   "linkedinUrl": "https://linkedin.com/in/johndoe",
#   "skills": ["Python", "Django", "FastAPI", ...],
#   "professionalBio": "Experienced software engineer...",
#   "step2Completed": true,
#   "idDocumentUrl": "/uploads/verification/abc123def456.pdf",
#   "idDocumentType": "passport",
#   "professionalCertificateUrl": "/uploads/verification/def456ghi789.pdf",
#   "step3Completed": true,
#   "status": "review",
#   "createdAt": "2026-03-23T10:00:00Z",
#   "updatedAt": "2026-03-23T10:15:00Z"
# }


# ──────────────────────────────────────────────────────────────────────────────
# STEP 4b: Final Submission
# ──────────────────────────────────────────────────────────────────────────────

print("\n" + "=" * 80)
print("STEP 4b: Submit Application")
print("=" * 80)

response = requests.post(
    f"{BASE_URL}/api/mentor/apply/step4",
    json={},
    headers=headers
)

print(f"Status: {response.status_code}")
print(f"Response:\n{json.dumps(response.json(), indent=2)}")

# Expected Response:
# {
#   "message": "Application submitted successfully. Please wait for admin review.",
#   "application": { ... }
# }

# At this point:
# - Application status: "submitted"
# - User verification_status: "pending"
# - User is_active: false (account deactivated until approved)


# ──────────────────────────────────────────────────────────────────────────────
# Check Status Anytime
# ──────────────────────────────────────────────────────────────────────────────

print("\n" + "=" * 80)
print("Check Application Status")
print("=" * 80)

response = requests.get(
    f"{BASE_URL}/api/mentor/application",
    headers=headers
)

print(f"Status: {response.status_code}")
print(f"Response:\n{json.dumps(response.json(), indent=2)}")

# Expected Response:
# {
#   "id": "app-123-uuid",
#   "mentorId": "mentor-456-uuid",
#   "status": "submitted",
#   "step1Completed": true,
#   "step2Completed": true,
#   "step3Completed": true,
#   "submittedAt": "2026-03-23T10:20:00Z",
#   "createdAt": "2026-03-23T10:00:00Z"
# }


# ──────────────────────────────────────────────────────────────────────────────
# FRONTEND IMPLEMENTATION NOTES
# ──────────────────────────────────────────────────────────────────────────────

"""
Frontend Implementation Guidelines
===================================

URL Routing:
  /mentor/register              → Basic registration (email, password)
  /mentor/apply/step1           → Personal Information form
  /mentor/apply/step2           → Professional Background form
  /mentor/apply/step3           → Document Upload form
  /mentor/apply/review          → Review & Submit page
  /mentor/apply/submitted       → Success page (show "awaiting review" message)

Form Validation:

Step 1:
  - Phone: Must be valid phone number format (consider libphonenumber)
  - Location: Non-empty string
  - Gender: Select from dropdown (Male, Female, Other, Prefer not to say)

Step 2:
  - Job Title: Non-empty, max 255 chars
  - Company: Optional, max 255 chars
  - Years Experience: Number >= 0
  - LinkedIn URL: Optional, must be valid URL if provided
  - Skills: Minimum 1 skill required, max 10 skills recommended
  - Professional Bio: Min 50 chars, max 5000 chars

Step 3:
  - ID Document: Required, PDF/JPG/PNG, max 5MB
  - ID Type: Select from "NIN", "Passport", "Driver's License"
  - Certificate: Required, PDF/JPG/PNG, max 5MB

State Management:
  - Save form data to local storage after each step
  - Show progress indicator (Step 1/4, 2/4, etc.)
  - Allow user to go back and edit previous steps before final submission
  - After submission, show waiting/pending state

Error Handling:
  - Display field-level validation errors
  - Show API error messages to user
  - Provide clear guidance on what went wrong
  - Allow retry for network errors

File Upload UX:
  - Show file preview/thumbnail
  - Display upload progress
  - Allow file replacement before proceeding
  - Show file size and format requirements

Review Page:
  - Display all information in read-only format
  - Show document previews/links
  - Provide "Edit" button to go back to specific step
  - Show "Submit" button that triggers final submission
  - After submission, prevent editing

Success State:
  - Show confirmation message
  - Display estimated review timeline ("typically 24-48 hours")
  - Provide support contact if issues arise
  - Disable mentor account until approved
"""
