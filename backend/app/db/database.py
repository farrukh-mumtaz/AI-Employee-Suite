from sqlmodel import create_engine, Session
from backend.app.core.config import DATABASE_URL

# Connection pooling settings:
# pool_size = how many connections stay ready and open at all times
# max_overflow = extra connections allowed temporarily if pool_size isn't enough
# pool_timeout = how long (seconds) to wait for a free connection before giving up
# pool_recycle = close and replace connections after this many seconds, to avoid stale/dead connections
# pool_pre_ping = check that a connection is still alive before using it (important for serverless DBs like Neon, which close idle connections)
engine = create_engine(
    DATABASE_URL,
    echo=True,
    pool_size=5,
    max_overflow=10,
    pool_timeout=30,
    pool_recycle=300,
    pool_pre_ping=True,
)

def get_session():
    with Session(engine) as session:
        yield session