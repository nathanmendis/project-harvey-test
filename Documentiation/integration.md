# Harvey Mock HRMS — Integration Guide

## Overview

The **Harvey Mock HRMS API** simulates an external HR system (similar to Workday / BambooHR) for integration testing. It exposes a read/write REST API over HTTP.

| Item                       | Value                          |
| -------------------------- | ------------------------------ |
| Base URL (local)           | `http://localhost:8001`        |
| Base URL (Docker internal) | `http://harvey-hrms-api:8001`  |
| API prefix                 | `/api/v1`                      |
| Auth method                | Static API Key via HTTP header |
| Data format                | JSON                           |
| Docs (Swagger)             | `http://localhost:8001/docs`   |

---

## Authentication

Every protected route requires the following HTTP header:

```
X-API-Token: harvey-secret-token-2026
```

> **Source:** `API_TOKEN` env var in `docker-compose.yml` / `.env`. Update the value in both places to rotate the token.

### Example (curl)

```bash
curl http://localhost:8001/api/v1/employees \
  -H "X-API-Token: harvey-secret-token-2026"
```

### Example (Python `requests`)

```python
import requests

BASE_URL = "http://localhost:8001/api/v1"
HEADERS  = {"X-API-Token": "harvey-secret-token-2026"}

resp = requests.get(f"{BASE_URL}/employees", headers=HEADERS)
employees = resp.json()
```

### Error Responses

| Status             | Meaning                         |
| ------------------ | ------------------------------- |
| `401 Unauthorized` | Header `X-API-Token` is missing |
| `403 Forbidden`    | Token value is wrong            |

---

## API Routes

### Health (no auth required)

| Method | Path      | Description              |
| ------ | --------- | ------------------------ |
| `GET`  | `/`       | Service status + version |
| `GET`  | `/health` | Liveness check           |

---

### Departments — `/api/v1/departments`

| Method | Path                                  | Description          |
| ------ | ------------------------------------- | -------------------- |
| `GET`  | `/api/v1/departments`                 | List all departments |
| `GET`  | `/api/v1/departments/{department_id}` | Get department by ID |

**Sample response:**

```json
{ "id": "dept-001", "name": "Engineering", "head": "emp-003", "headcount": 28 }
```

---

### Employees — `/api/v1/employees`

| Method | Path                                      | Query Params                          | Description             |
| ------ | ----------------------------------------- | ------------------------------------- | ----------------------- |
| `GET`  | `/api/v1/employees`                       | `department_id`, `status`, `location` | List / filter employees |
| `GET`  | `/api/v1/employees/{employee_id}`         | —                                     | Get employee by ID      |
| `GET`  | `/api/v1/employees/{employee_id}/reports` | —                                     | Get direct reports      |
| `GET`  | `/api/v1/employees/search/by-email`       | `email` (required)                    | Lookup by email         |
| `GET`  | `/api/v1/employees/search/by-name`        | `name` (required)                     | Partial name search     |

**Filter example:**

```
GET /api/v1/employees?status=active&department_id=dept-001
```

**Status values:** `active`, `on_leave`, `terminated`

---

### Job Postings — `/api/v1/jobs`

| Method | Path                    | Query Params              | Description               |
| ------ | ----------------------- | ------------------------- | ------------------------- |
| `GET`  | `/api/v1/jobs`          | `status`, `department_id` | List / filter jobs        |
| `GET`  | `/api/v1/jobs/open`     | —                         | Shortcut — open jobs only |
| `GET`  | `/api/v1/jobs/{job_id}` | —                         | Get job by ID             |

**Status values:** `open`, `closed`, `draft`, `on_hold`

---

### Candidates — `/api/v1/candidates`

| Method  | Path                                       | Query Params / Body         | Description              |
| ------- | ------------------------------------------ | --------------------------- | ------------------------ |
| `GET`   | `/api/v1/candidates`                       | `job_id`, `status`, `stage` | List / filter candidates |
| `GET`   | `/api/v1/candidates/{candidate_id}`        | —                           | Get candidate by ID      |
| `GET`   | `/api/v1/candidates/search/by-email`       | `email` (required)          | Lookup by email          |
| `PATCH` | `/api/v1/candidates/{candidate_id}/status` | JSON body                   | Update status + notes    |

**PATCH body:**

```json
{
  "status": "shortlisted",
  "notes": "Passed technical round."
}
```

**Status values:** `applied`, `under_review`, `interview_scheduled`, `offer_extended`, `offer_accepted`, `rejected`, `withdrawn`

**Stage values:** `applied`, `hr_screening`, `technical_round`, `final_round`, `offer`, `rejected`

---

### Interviews — `/api/v1/interviews`

| Method  | Path                                         | Query Params / Body                | Description              |
| ------- | -------------------------------------------- | ---------------------------------- | ------------------------ |
| `GET`   | `/api/v1/interviews`                         | `candidate_id`, `job_id`, `status` | List / filter interviews |
| `GET`   | `/api/v1/interviews/{interview_id}`          | —                                  | Get interview by ID      |
| `POST`  | `/api/v1/interviews`                         | JSON body                          | Schedule a new interview |
| `PATCH` | `/api/v1/interviews/{interview_id}/feedback` | JSON body                          | Submit feedback + score  |
| `PATCH` | `/api/v1/interviews/{interview_id}/cancel`   | —                                  | Cancel interview         |

**POST body — Schedule Interview:**

```json
{
  "candidate_id": "cand-001",
  "job_id": "job-001",
  "interview_type": "technical",
  "round": 2,
  "scheduled_at": "2026-03-15T10:00:00",
  "duration_minutes": 60,
  "interviewers": ["emp-002", "emp-003"],
  "location": "Google Meet",
  "meet_link": "https://meet.google.com/abc-xyz",
  "notes": "Focus on system design."
}
```

**PATCH body — Feedback:**

```json
{ "feedback": "Excellent communicator.", "score": 4.5 }
```

**Interview type values:** `hr_screening`, `technical`, `system_design`, `behavioral`, `final`, `culture_fit`

---

### Onboarding — `/api/v1/onboarding`

| Method  | Path                                        | Query Params        | Description                      |
| ------- | ------------------------------------------- | ------------------- | -------------------------------- |
| `GET`   | `/api/v1/onboarding`                        | `status`            | List / filter onboarding records |
| `GET`   | `/api/v1/onboarding/{onboarding_id}`        | —                   | Get record by ID                 |
| `GET`   | `/api/v1/onboarding/employee/{employee_id}` | —                   | Get record by employee           |
| `PATCH` | `/api/v1/onboarding/{onboarding_id}/task`   | `task_name` (query) | Mark a task as done              |

**PATCH example — Complete a task:**

```
PATCH /api/v1/onboarding/onb-001/task?task_name=IT+Setup
```

**Onboarding status values:** `pending`, `in_progress`, `completed`

---

## ID Reference

All IDs follow predictable patterns seeded in the DB:

| Entity      | ID format               | Range       |
| ----------- | ----------------------- | ----------- |
| Department  | `dept-001` … `dept-010` | 10 records  |
| Employee    | `emp-001` … `emp-100`   | 100 records |
| Job Posting | `job-001` … `job-100`   | 100 records |
| Candidate   | `cand-001` … `cand-100` | 100 records |
| Interview   | `int-001` … `int-100`   | 100 records |
| Onboarding  | `onb-001` … `onb-100`   | 100 records |

---

## Environment Variables

| Variable            | Default                             | Description                                         |
| ------------------- | ----------------------------------- | --------------------------------------------------- |
| `POSTGRES_USER`     | `harvey`                            | DB username                                         |
| `POSTGRES_PASSWORD` | `harvey123`                         | DB password                                         |
| `POSTGRES_DB`       | `harvey_hrms`                       | Database name                                       |
| `POSTGRES_HOST`     | `db` (Docker) / `localhost` (local) | DB host                                             |
| `POSTGRES_PORT`     | `5435`                              | DB port                                             |
| `API_TOKEN`         | `harvey-secret-token-2026`          | Auth token — set in `.env` and `docker-compose.yml` |

---

## Running the API

### With Docker (recommended)

```bash
docker compose up -d
# API: http://localhost:8001
# DB:  localhost:5435
```

### Locally (dev)

```bash
python -m venv .venv && .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
```

### Reset data

```bash
docker compose down -v   # drops DB volume
docker compose up -d     # recreates and re-seeds
```
