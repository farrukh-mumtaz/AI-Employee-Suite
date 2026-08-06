# Root pytest conftest.
#
# Ensures every SQLModel table (including `document`) exists *before* any
# test module is collected. Table creation normally only happens in
# backend/app/main.py's FastAPI `on_startup` handler, which never runs for
# tests that hit the DB/retrieval layer directly instead of going through
# the app's lifespan (e.g. test_full_flow.py, and the real-engine cases in
# test_retrieval.py) -- causing `sqlite3.OperationalError: no such table:
# document`.
#
# This has to run as top-level module code, not inside a fixture:
# test_full_flow.py has no test_* functions -- it's a script that runs at
# import/collection time -- so a fixture would never get a chance to run
# first. conftest.py, however, is always imported before any test module in
# the same directory tree, so module-level code here is guaranteed to run
# first regardless of how a given test file is structured.
#
# DATABASE_URL is redirected to a throwaway SQLite file instead of the
# git-tracked app.db, so running the suite never leaves modified DB state
# to accidentally commit, and every run starts from the same clean schema.
import os
import tempfile

_TEST_DB_PATH = os.path.join(tempfile.gettempdir(), "ai_employee_suite_test.db")
if os.path.exists(_TEST_DB_PATH):
    os.remove(_TEST_DB_PATH)

os.environ["DATABASE_URL"] = f"sqlite:///{_TEST_DB_PATH}"

from sqlmodel import SQLModel  # noqa: E402
from backend.app import models  # noqa: E402, F401 -- registers all tables on SQLModel.metadata
from backend.app.db.database import engine  # noqa: E402

SQLModel.metadata.create_all(engine)
