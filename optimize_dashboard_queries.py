from sqlalchemy import text
from backend.app.db.database import engine

# These indexes speed up the dashboard queries, since they filter/group/sort
# by these columns frequently (agent_name, created_at, status).
with engine.connect() as conn:
    conn.execute(text("CREATE INDEX IF NOT EXISTS idx_agentlog_agent_name ON agentlog (agent_name)"))
    conn.execute(text("CREATE INDEX IF NOT EXISTS idx_agentlog_created_at ON agentlog (created_at)"))
    conn.execute(text("CREATE INDEX IF NOT EXISTS idx_leaverequest_status ON leaverequest (status)"))
    conn.commit()
    print("Dashboard query indexes created!")