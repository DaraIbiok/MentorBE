# Matching Algorithm — `GET /api/mentors/recommended`

## Overview

When a mentee requests recommended mentors, the backend computes a **match score**
for every active mentor and returns the list sorted by:

1. **Match score** (descending)
2. **Average rating** (descending)
3. **Rating count** (descending)

---

## How the score is calculated

```
match_score(mentee, mentor) = |mentee_interests ∩ mentor_skills|
```

Where:

- **`mentee_interests`** = union of `mentee.skills` + `mentee.goals` (lowercased, split by comma)
- **`mentor_skills`** = `mentor.skills` (lowercased, split by comma)

### Example

| Field | Value |
|-------|-------|
| Mentee skills | `"Python, Machine Learning"` |
| Mentee goals | `"Get a data job, Learn ML"` |
| Mentor A skills | `"Python, SQL, Machine Learning"` |
| Mentor B skills | `"React, Node.js, TypeScript"` |

**Mentee interests set:** `{python, machine learning, get a data job, learn ml}`

- **Mentor A score:** 2 (`python`, `machine learning` both match)
- **Mentor B score:** 0 (no overlap)

→ Mentor A ranks above Mentor B.

---

## Extending the algorithm

The current implementation is intentionally simple. To improve match quality:

### Option 1 — Weighted fields
Give `goals` a higher weight than `skills` (e.g. 2× multiplier).

### Option 2 — Semantic similarity
Use an embedding model (e.g. OpenAI `text-embedding-3-small`) to compute
cosine similarity between mentee goals and mentor bios/skills.

### Option 3 — Engagement signals
Factor in: mentor response rate, acceptance rate, number of completed sessions.

### Option 4 — Collaborative filtering
"Mentees similar to you also booked mentor X" — requires session history data.

---

## Location in code

`app/api/routes/mentors.py` → `_match_score()` and `recommended_mentors()`
