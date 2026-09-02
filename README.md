# HireFlow AI

A production-oriented recruiting platform starter with a Next.js dashboard, FastAPI API, Supabase PostgreSQL, and container builds suitable for local development and AWS ECS.

## Architecture

- `frontend/` — Next.js App Router, React, TypeScript, Tailwind CSS, and shadcn/ui-compatible components
- `backend/` — Python 3.12, FastAPI, Pydantic, SQLAlchemy, and PostgreSQL
- `docker-compose.yml` — local frontend and backend connected to Supabase PostgreSQL
- Separate production-ready Dockerfiles for independent frontend and backend ECS services

## Local development with Docker

1. Create a local environment file:

   ```bash
   cp .env.example .env
   ```

2. In Supabase, open **Connect**, select the **Session pooler** connection string, and
   place it in `DATABASE_URL`. The direct `db.<project-ref>.supabase.co` connection commonly
   requires IPv6 and may be unreachable from Docker Desktop. Keep `DATABASE_SSL=true`.
   URL-encode special characters in the password—for example, `@` becomes `%40`.

   If you already have the direct Supabase URL in `DATABASE_URL`, you can instead set
   `SUPABASE_POOLER_HOST` to the Session pooler hostname shown by Supabase. HireFlow will
   preserve the existing credentials and safely construct the pooler connection internally.

3. Build and start the stack:

   ```bash
   docker compose up --build
   ```

   Compose loads backend settings from `.env`, builds the browser API URL from
   `NEXT_PUBLIC_API_URL`, and starts both services. The frontend remains available to show
   useful API errors if the backend is unhealthy. The backend health check verifies its
   Supabase database connection.

4. Open:

   - Dashboard: http://localhost:3000
   - API health: http://localhost:8000/health
   - API docs: http://localhost:8000/docs

Stop the stack with `docker compose down`. Supabase data is external and is not removed by this command.

Both services use `restart: unless-stopped`. Local ports are intentionally fixed:
frontend `3000` and backend `8000`.

### Docker troubleshooting

Check container and health state:

```bash
docker compose ps
docker compose logs --tail=100 backend frontend
curl --fail http://localhost:8000/health
curl --fail http://localhost:3000
```

If Docker reports that port `3000` or `8000` is already allocated, identify the process
using the port, stop that process or its old container, then start HireFlow again:

```bash
lsof -nP -iTCP:3000 -sTCP:LISTEN
lsof -nP -iTCP:8000 -sTCP:LISTEN
docker compose down
docker compose up --build
```

If the backend is unhealthy, verify that the Supabase project is running, the connection
string is the Session pooler URL, `DATABASE_SSL=true`, and password special characters are
URL-encoded. A `Network is unreachable` error for an IPv6 address normally means the direct
Supabase connection string was used instead of the pooler.
Then recreate the backend container after updating `.env`:

```bash
docker compose up -d --build --force-recreate backend
docker compose logs --tail=200 backend
```

If the frontend still calls an old backend URL, confirm `NEXT_PUBLIC_API_URL` in `.env` and
rebuild the frontend; this public value is embedded during `next build`:

```bash
docker compose build --no-cache frontend
docker compose up -d
```

If a container is unhealthy, inspect its own health output and recent logs:

```bash
docker inspect --format '{{json .State.Health}}' hireflow-ai-backend-1
docker compose logs --tail=200 backend
```

Groq, Apollo and Hunar keys may remain blank when validating the base stack. Their specific
API operations return configuration errors until the corresponding backend-only key is set.

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
export DATABASE_URL='postgresql://POOLER_USER:URL_ENCODED_PASSWORD@POOLER_HOST:5432/postgres'
export FRONTEND_URL='http://localhost:3000'
export DATABASE_SSL='true'
uvicorn app.main:app --reload
```

The backend creates the `jobs`, `candidates`, `calls`, and `webhook_events` tables in Supabase on startup. To initialize them explicitly, run `python -m app.init_db` from `backend/`. Common `postgres://` and `postgresql://` URLs are normalized automatically to the Psycopg 3 SQLAlchemy dialect. Keep credentials in environment variables or your deployment secret store.

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

## Recruiter dashboard

The responsive Next.js recruiter workspace includes:

- `/` — live hiring totals and recent AI screening calls
- `/jobs/new` — Groq-assisted JD analysis, editing, saving and Apollo search
- `/candidates` — job filtering, saved-contact search, manual candidates, phone editing and confirmed AI call initiation
- `/calls` — Hunar status, screening insights, summaries, recordings and refresh controls
- `/attendance` — Assignment 3 attendance architecture proposal

Browser API requests use only `NEXT_PUBLIC_API_URL`. Provider credentials remain backend-only environment variables. Apollo sourcing is clearly labeled as a search of contacts already saved in the configured Apollo workspace, and every voice-screening action requires confirmation that the call will be made by an AI agent.

## Hunar Voice calls

Set `HUNAR_API_KEY` and set `PUBLIC_BACKEND_URL` to the externally reachable HTTPS backend URL. An `http://localhost` value is sufficient for the base stack but is intentionally rejected when initiating a Hunar call because Hunar requires HTTPS callback URLs and cannot reach the developer's localhost. For local call testing, keep an HTTPS tunnel to port 8000 running for the complete call and set `PUBLIC_BACKEND_URL` to its public origin before recreating the backend container. Hunar agent and call endpoints are:

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
npm run lint
npm run type-check
NEXT_PUBLIC_API_URL=http://localhost:8000 npm run build

cd ../backend
pip install -r requirements-dev.txt
pytest
python -m compileall -q app tests
```

With Docker installed, validate and build the images:

```bash
docker compose config --quiet
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
