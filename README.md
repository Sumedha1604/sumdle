# Sumdle

Sumdle is a React/Vite word game with a FastAPI backend, curated daily and
unlimited puzzles, persistent validation caching, and optional MCP dictionary
enrichment.

## Local Development

Install frontend dependencies with `npm install`. Create a Python virtual
environment and install `pip install -r backend/requirements.txt`. Run FastAPI
with `uvicorn backend.app:app --reload`, then run the frontend with `npm run dev`.
Run backend tests with `python -m pytest`.

Without a frontend environment file, Vite proxies relative `/api` requests to
local FastAPI. Copy `.env.example` to `.env` only when an explicit API URL is
needed. Never commit `.env` files or production connection strings.

## Environment Variables

| Variable | Used by | Purpose |
| --- | --- | --- |
| `VITE_API_BASE_URL` | Vercel/frontend | Public Render API URL. Leave blank only for same-origin hosting. |
| `DATABASE_URL` | Render/backend | Neon PostgreSQL connection string. Omit locally for SQLite. |
| `CORS_ORIGINS` | Render/backend | Comma-separated allowlist, including local Vite and Vercel origins. |
| `SUMDLE_MCP_COMMAND` | Backend | Optional stdio MCP executable. |
| `SUMDLE_MCP_ARGS` | Backend | Optional JSON argument array for that executable. |
| `SUMDLE_MCP_CWD` | Backend | Optional MCP working directory. |
| `SUMDLE_MCP_TIMEOUT_SECONDS` | Backend | Optional lookup timeout; defaults to `3`. |

## Database Configuration

Without `DATABASE_URL`, Sumdle uses SQLite at `backend/data/sumdle.db`. With a
`postgresql://...` URL, it uses PostgreSQL via `psycopg`; Neon's connection URL
works directly, including its `sslmode=require` parameter. The data model keeps
the `solutions` and `word_validation_cache` tables.

Schema changes are versioned in `backend/migrations.py`. At startup the backend
records and applies only pending migrations in `schema_migrations`; it does not
recreate a database or delete data. Curated solution seeding is idempotent.

## Free Deployment Stack

This repository is set up for Vercel Hobby, a Render Free web service, and Neon
Free PostgreSQL. Use only their free plans; do not upgrade or add billing.
Free services have provider limits, including Render idle spin-down, so the
first request after inactivity can be slow.

### Neon

1. Create a free Neon Postgres project.
2. Copy its PostgreSQL connection string (keep the supplied SSL query option).
3. In Render, set `DATABASE_URL` to that value. It is a secret—never put it in
   `.env.example`, source code, or Vercel variables.

### Render

1. Connect the GitHub repository and create a **Web Service** on the Free plan.
2. Render can use the committed `render.yaml`, or enter its equivalent settings:
   build command `pip install -r backend/requirements.txt` and start command
   `uvicorn backend.app:app --host 0.0.0.0 --port $PORT`.
   Keep **Root Directory** blank (repository root) because the start command
   imports `backend.app`; select the `main` branch and a region close to the
   Neon project.
3. Set `DATABASE_URL` from Neon and initially set
   `CORS_ORIGINS=http://localhost:5173`. Add the Vercel URL after the frontend
   is deployed, for example `http://localhost:5173,https://your-app.vercel.app`.
4. Deploy and verify `https://YOUR-RENDER-SERVICE.onrender.com/health` returns
   `{"status":"ok"}`. This liveness endpoint never calls MCP or the database.

`render.yaml` deploys only the Python backend from this monorepo. The Render
filesystem is ephemeral, which is why deployed instances must use Neon instead
of SQLite.

### Vercel

1. Import the GitHub repository into Vercel on the Hobby plan.
2. Keep the root directory at the repository root; Vercel detects Vite and uses
   `npm run build` to create `dist`. No `vercel.json` is required.
3. Add `VITE_API_BASE_URL=https://YOUR-RENDER-SERVICE.onrender.com` in Vercel's
   production environment variables, then deploy.
4. Copy the resulting `https://YOUR-APP.vercel.app` URL into Render's
   `CORS_ORIGINS` and redeploy the backend.

The frontend has no production localhost default: it reads
`VITE_API_BASE_URL`, while the local Vite proxy remains available for
development.

## MCP Configuration

Sumdle can ask the [Word of the Day MCP server](https://github.com/Traves-Theberge/Word_of_the_day)
about unknown guesses. For a local setup, clone and build it separately:

```sh
export SUMDLE_MCP_COMMAND=node
export SUMDLE_MCP_ARGS='["dist/index.js"]'
export SUMDLE_MCP_CWD=/path/to/Word_of_the_day
export SUMDLE_MCP_TIMEOUT_SECONDS=3
```

The current integration launches a local stdio process. It is **not** bundled
into this Render deployment, so leave the MCP command unset on Render unless
you deliberately package that server and its Node dependencies into the backend
runtime. MCP is optional: outages return an understandable fallback and do not
break cached or normal gameplay.

## Notes

Daily puzzles use the backend server date, SHA-256 of its ISO form, and sorted
active solutions. The current React evaluator receives the solution from the
API for gameplay; it is not a security boundary. Move evaluation server-side
before answers need to remain secret.
