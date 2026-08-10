# Deployment Guide — AI Employee Suite Backend

## Prerequisites

- Python 3.11+
- A PostgreSQL database with the pgvector extension available (currently using Neon)
- Environment variables set (see below)

## Environment Variables

Create a .env file in the project root with the following:

DATABASE_URL=postgresql+psycopg2://<user>:<password>@<host>/<db>?sslmode=require
JWT_SECRET_KEY=<a long, random secret string>
GROQ_API_KEY=<your Groq API key>
ENVIRONMENT=production

Important: never commit .env to version control. It is already excluded via .gitignore.

## Local Setup (Development)

1. Create and activate a virtual environment:
   python -m venv venv
   venv\Scripts\activate      # Windows
   source venv/bin/activate   # Mac/Linux

2. Install dependencies:
   pip install -r requirements.txt

3. Run the server:
   uvicorn backend.app.main:app --reload

4. Visit http://127.0.0.1:8000/docs to confirm it's running.

Tables are created automatically on startup (SQLModel.metadata.create_all), so no separate migration step is needed for this stage of the project.

## Production Deployment (Recommended: Railway or Render)

1. Push the latest code to the main branch (via an approved PR).
2. Create a new Web Service on Railway/Render, connected to this GitHub repository.
3. Set the build command:
   pip install -r requirements.txt
4. Set the start command:
   uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT
5. Add the environment variables listed above in the platform's dashboard.
6. Deploy.

## Database Notes

- Using Neon (serverless Postgres). Connection pooling is configured with pool_pre_ping=True to handle Neon's idle connection timeouts gracefully.
- The pgvector extension must be enabled on the production database as well (enable_pgvector.py can be run once against the production DB).

## Post-Deployment Checklist

- [ ] Confirm /health returns 200 OK
- [ ] Confirm /docs loads
- [ ] Create the first admin user and verify admin-only endpoints work
- [ ] Run regression_test.py against the deployed URL
- [ ] Confirm error logging (ErrorLog table) is capturing issues if any occur

## Known Limitations

- No dedicated frontend/dashboard UI exists yet.
- Rate limiting is not yet implemented; recommended before public/production use at scale.
- Multiple orchestration implementations currently exist and should be consolidated.