# HireFlow AI

A production-oriented recruiting platform starter with a Next.js dashboard, FastAPI API, PostgreSQL, and container builds suitable for local development and AWS ECS.

## Architecture

- `frontend/` — Next.js App Router, React, TypeScript, Tailwind CSS, and shadcn/ui-compatible components
- `backend/` — Python 3.12, FastAPI, Pydantic, SQLAlchemy, and PostgreSQL
- `docker-compose.yml` — local frontend, backend, and PostgreSQL stack
- Separate production-ready Dockerfiles for independent frontend and backend ECS services

## Local development with Docker

1. Create a local environment file:

   ```bash
   cp .env.example .env
   ```

2. Replace the example database password in `.env`. Keep `POSTGRES_PASSWORD` and the password embedded in `DATABASE_URL` identical.

3. Build and start the stack:

   ```bash
   docker compose up --build
   ```

4. Open:

   - Dashboard: http://localhost:3000
   - API health: http://localhost:8000/health
   - API docs: http://localhost:8000/docs

Stop the stack with `docker compose down`. Add `--volumes` only when you intentionally want to remove local PostgreSQL data.

## Run services directly

### Frontend

```bash
cd frontend
npm ci
npm run dev
```

### Backend

```bash
cd backend
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export DATABASE_URL='postgresql+psycopg://hireflow:password@localhost:5432/hireflow'
export FRONTEND_URL='http://localhost:3000'
export DATABASE_SSL='false'
uvicorn app.main:app --reload
```

The backend creates the `jobs`, `candidates`, `calls`, and `webhook_events` tables on startup. To initialize them explicitly, run `python -m app.init_db` from `backend/`.

For Supabase, use its PostgreSQL connection string as `DATABASE_URL` and set `DATABASE_SSL=true`. Common `postgres://` and `postgresql://` URLs are normalized automatically to the Psycopg 3 SQLAlchemy dialect. Keep credentials in environment variables or your deployment secret store.

## Job analysis API

Set `GROQ_API_KEY` in `.env`. The backend uses `openai/gpt-oss-120b` with temperature `0`; the key is never returned or logged.

Analyze a job description:

```bash
curl -X POST http://localhost:8000/api/jobs/analyze \
  -H 'Content-Type: application/json' \
  -d '{"description":"We are hiring a Senior Python Backend Engineer in Bengaluru. Build FastAPI services using PostgreSQL and Docker. Requires 4 to 7 years of experience."}'
```

Save the analysis by posting the original description together with the analysis fields:

```bash
curl -X POST http://localhost:8000/api/jobs \
  -H 'Content-Type: application/json' \
  -d '{
    "description": "We are hiring a Senior Python Backend Engineer in Bengaluru with 4 to 7 years of experience using FastAPI, PostgreSQL, and Docker.",
    "job_title": "Senior Python Backend Engineer",
    "skills": ["Python", "FastAPI", "PostgreSQL", "Docker"],
    "location": "Bengaluru",
    "minimum_experience": 4,
    "maximum_experience": 7,
    "seniority": "Senior",
    "search_keywords": "Senior Python Backend Engineer FastAPI PostgreSQL Docker Bengaluru"
  }'
```

List jobs with `GET /api/jobs` and retrieve one with `GET /api/jobs/{id}`. List requests support `offset` and `limit` query parameters.

## Apollo candidate search

Set `APOLLO_API_KEY` in `.env`, then call:

```bash
curl -X POST http://localhost:8000/api/jobs/JOB_UUID/search-candidates
```

This integration uses Apollo's `POST /api/v1/contacts/search` endpoint. It searches only contacts already saved in your team's Apollo workspace; it does not search Apollo's broader people database. The saved job's `search_keywords` are sent as `q_keywords`, with `page=1` and `per_page=10`.

If the keyword search returns no contacts, HireFlow retries once without `q_keywords`. The response sets `fallback_without_keywords=true` and clearly labels those unfiltered workspace contacts as recruiter-review candidates, not guaranteed job matches.

Candidate endpoints:

- `GET /api/candidates?job_id=JOB_UUID`
- `PATCH /api/candidates/CANDIDATE_UUID/phone` with `{"phone":"+919999999999"}`
- `POST /api/candidates/manual` with `job_id`, `name`, `phone`, and `email`

Apollo candidates are deduplicated per job using `(job_id, apollo_id)`, while the complete Apollo contact object is retained in `raw_profile`. API credentials and complete request headers are never logged.

## Hunar Voice calls

Set `HUNAR_API_KEY` and set `PUBLIC_BACKEND_URL` to the externally reachable backend URL. Hunar agent and call endpoints are:

- `GET /api/hunar/agents`
- `GET /api/hunar/agents/{agent_id}`
- `POST /api/calls` with `candidate_id`, `agent_id`, and optional `custom_data`
- `GET /api/calls`, optionally filtered by `job_id` or `candidate_id`
- `GET /api/calls/{id}`
- `POST /api/calls/{id}/refresh`

Creating a call requires the candidate phone number to use E.164 format, such as `+919999999999`. HireFlow loads the selected Hunar agent first and sends every custom-data variable marked as required by that agent. The standard `job_role`, `job_description`, `company`, and `location` values are included only when the agent requires them. Other required variables must be supplied in the request's `custom_data` object.

Each call receives a local UUID request ID and is saved as `REQUESTED` before the provider request is made. The configured callbacks are:

- `{PUBLIC_BACKEND_URL}/webhooks/hunar/status`
- `{PUBLIC_BACKEND_URL}/webhooks/hunar/recording`
- `{PUBLIC_BACKEND_URL}/webhooks/hunar/result`
- `{PUBLIC_BACKEND_URL}/webhooks/hunar/summary`

Refresh retrieves the current provider call and updates its status, duration, recording URL, result, summary, and retained raw response. Provider validation, authentication, subscription, missing-resource, rate-limit, timeout, and server failures return distinct API errors without exposing credentials. Phone numbers and the Hunar API key are not logged. Bulk calling is intentionally not implemented.

Hunar sends status, recording, result, and summary updates to the four callback URLs. Each webhook must include `X-Hunar-Timestamp` and `X-Hunar-Signature`. HireFlow verifies a Base64-encoded HMAC SHA-256 signature over `{timestamp}.{raw_request_body}` using `HUNAR_API_KEY` and rejects timestamps outside a five-minute window. Valid payloads are retained in `webhook_events`; identical retries are safely acknowledged without applying the event twice.

## Validation

```bash
cd frontend
npm run type-check
npm run build

cd ../backend
pip install -r requirements-dev.txt
pytest
python -m compileall -q app tests
```

With Docker installed, validate and build the images:

```bash
docker compose --env-file .env.example config --quiet
docker build -t hireflow-ai-backend ./backend
docker build --build-arg NEXT_PUBLIC_API_URL=https://api.example.com -t hireflow-ai-frontend ./frontend
```

## Production deployment notes

- Build and publish `frontend/Dockerfile` and `backend/Dockerfile` independently to Amazon ECR, then deploy them as separate ECS services.
- Supply runtime values through ECS task-definition environment variables or AWS Secrets Manager. Do not bake credentials into images.
- Set `DATABASE_URL` to the RDS or Supabase PostgreSQL connection string and `FRONTEND_URL` to a comma-separated list of deployed frontend origins.
- Set `DATABASE_SSL=true` for Supabase or any PostgreSQL service that requires TLS.
- Pass `NEXT_PUBLIC_API_URL` as a frontend image build argument because browser-visible Next.js variables are embedded during `next build`.
- Set `INTERNAL_API_URL` at runtime for future server-side frontend requests.
- Terminate TLS and route traffic with an Application Load Balancer. Run database migrations as a separate ECS task when schema migrations are introduced.

No API keys or credentials are committed. `.env` and `.env.local` are ignored by Git.
