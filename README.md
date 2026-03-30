# MentorMe — Backend API

FastAPI + MySQL backend for the MentorMe mentorship platform.  
Authentication is handled by **Supabase** on the frontend; this backend **validates Supabase JWTs** and manages all business logic.

---

## Tech stack

| Layer | Technology |
|-------|-----------|
| Framework | FastAPI 0.111 |
| Database | MySQL 8+ via SQLAlchemy 2 + PyMySQL |
| Auth | Supabase JWT (HS256 validation) |
| Migrations | Alembic |
| File uploads | Local disk (default) or AWS S3 |
| Video rooms | Daily.co REST API |
| Python | 3.11+ |

---

## Project structure

```
mentorme-backend/
├── main.py                        # FastAPI app, routers, CORS, static files
├── requirements.txt
├── .env.example                   # Copy to .env and fill in values
├── alembic.ini
├── alembic/
│   ├── env.py
│   └── versions/
│       └── 0001_initial.py        # Creates all tables
├── docs/
│   └── MATCHING_ALGORITHM.md      # How /api/mentors/recommended works
└── app/
    ├── core/
    │   ├── config.py              # Pydantic settings (reads .env)
    │   └── auth.py                # JWT validation + user sync dependency
    ├── db/
    │   └── database.py            # SQLAlchemy engine + get_db()
    ├── models/
    │   └── models.py              # ORM: users, requests, sessions, messages, ratings
    ├── schemas/
    │   └── schemas.py             # Pydantic v2 request/response schemas
    ├── services/
    │   ├── upload_service.py      # File upload (local or S3)
    │   └── video_service.py       # Daily.co room management
    └── api/routes/
        ├── auth.py                # GET /api/auth/me
        ├── profile.py             # GET/PATCH /api/profile, POST /api/profile/avatar
        ├── mentors.py             # GET /api/mentors, /recommended, /:id, /:id/ratings
        ├── requests.py            # POST /api/requests, GET/PATCH /api/mentor/requests
        ├── sessions.py            # Full session CRUD + room + messages + ratings
        ├── mentor_mentees.py      # GET /api/mentor/mentees, /:menteeId
        └── admin.py               # GET /api/admin/users, /sessions + activate/deactivate
```

---

## Quick start

### 1. Clone and set up Python environment

```bash
cd mentorme-backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
```

Open `.env` and fill in:

```env
DATABASE_URL=mysql+pymysql://root:yourpassword@localhost:3306/mentorme
SUPABASE_JWT_SECRET=your-jwt-secret    # Supabase dashboard → Settings → API → JWT Settings
SUPABASE_URL=https://xxxx.supabase.co
SUPABASE_ANON_KEY=your-anon-key
```

### 3. Create the MySQL database

```sql
CREATE DATABASE mentorme CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

### 4. Run database migrations

```bash
alembic upgrade head
```

> **Shortcut for development:** If you skip Alembic, `main.py` calls  
> `Base.metadata.create_all()` on startup which creates tables automatically.

### 5. Start the server

```bash
uvicorn main:app --reload --port 4000
```

API docs available at: `http://localhost:4000/docs`

---

## Frontend connection

In your React project's `.env`:

```env
VITE_API_URL=http://localhost:4000
```

---

## Authentication flow

```
User logs in via Supabase (frontend)
  → Supabase returns JWT access token
  → Frontend sends: Authorization: Bearer <token>
  → Backend decodes JWT with SUPABASE_JWT_SECRET
  → Backend looks up User by supabase_id (creates row on first call)
  → Backend syncs role from JWT user_metadata.role
  → Request proceeds with current_user injected via Depends()
```

---

## API reference (all endpoints)

### Auth
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/auth/me` | ✅ | Return current user |

### Profile
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/profile/me` | ✅ | Get profile |
| PATCH | `/api/profile` | ✅ | Update name, bio, skills, goals, role, etc. |
| POST | `/api/profile/avatar` | ✅ | Upload avatar image |

### Mentors
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/mentors` | ✅ | List all mentors |
| GET | `/api/mentors/recommended` | mentee | Personalised ranked list |
| GET | `/api/mentors/:id` | ✅ | Single mentor profile |
| GET | `/api/mentors/:id/ratings` | ✅ | Ratings received by mentor |

### Requests
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/requests` | mentee | Create mentorship request |
| GET | `/api/mentor/requests` | mentor | List incoming requests |
| PATCH | `/api/mentor/requests/:id` | mentor | Accept or decline |

### Sessions
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/sessions` | ✅ | List sessions for current user |
| POST | `/api/sessions` | mentee | Create session |
| GET | `/api/sessions/:id` | participant | Session detail + messages |
| PATCH | `/api/sessions/:id` | participant | Update status |
| POST | `/api/sessions/:id/room` | participant | Get/create video room URL |
| POST | `/api/sessions/:id/messages` | participant | Send chat message |
| GET | `/api/sessions/:id/ratings` | participant | List ratings |
| POST | `/api/sessions/:id/ratings` | participant | Submit/update rating |

### Mentor → Mentees
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/mentor/mentees` | mentor | List mentees with progress |
| GET | `/api/mentor/mentees/:menteeId` | mentor | Mentee detail + sessions |

### Admin
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/admin/users` | admin | List all users |
| PATCH | `/api/admin/users/:id/deactivate` | admin | Deactivate user |
| PATCH | `/api/admin/users/:id/activate` | admin | Reactivate user |
| GET | `/api/admin/sessions` | admin | List all sessions |

---

## File uploads

**Default (local):** Files saved to `./uploads/` and served at `/uploads/...`  
**Switch to S3:** Set `UPLOAD_PROVIDER=s3` and fill in `AWS_*` values in `.env`

Max file size: 5 MB (configurable via `MAX_UPLOAD_BYTES`)  
Allowed types: `.jpg .jpeg .png .gif .webp .pdf .doc .docx .txt .md`

---

## Video rooms (Daily.co)

1. Sign up at [daily.co](https://www.daily.co) and get an API key
2. Set `DAILY_API_KEY=your-key` in `.env`
3. Rooms are auto-created on `POST /api/sessions/:id/room` and the URL is stored in the session row

**Without a key:** A mock URL is returned so development still works.

---

## Production deployment checklist

- [ ] Set `APP_ENV=production`
- [ ] Use a strong random `SECRET_KEY`
- [ ] Set `ALLOWED_ORIGINS` to your frontend domain
- [ ] Use Alembic for all schema changes (remove `create_all` from `main.py`)
- [ ] Switch `UPLOAD_PROVIDER=s3` for file storage
- [ ] Run behind a reverse proxy (nginx / Caddy) with HTTPS
- [ ] Use a production WSGI server: `gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker`
