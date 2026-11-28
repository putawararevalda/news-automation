from typing import Generator
from sqlalchemy import event
from sqlmodel import SQLModel, create_engine, Session

from backend.app.config import settings

connect_args = {"check_same_thread": False, "timeout": 15}

engine = create_engine(
    settings.database_url,
    echo=False,
    connect_args=connect_args,
)


@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    """Enable WAL mode, foreign keys, and busy timeout for concurrent access."""
    cursor = dbapi_connection.cursor()
    try:
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA busy_timeout=5000")
    finally:
        cursor.close()


def init_db() -> None:
    """Create all SQLModel tables in database."""
    SQLModel.metadata.create_all(engine)


def get_session() -> Generator[Session, None, None]:
    """Dependency for yielding database session."""
    with Session(engine) as session:
        yield session
