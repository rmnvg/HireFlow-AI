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
