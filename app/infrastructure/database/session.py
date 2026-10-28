from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker, Session
from typing import Generator
from app.core.config import settings, ROOT_DIR

def get_engine_url() -> str:
    url = settings.database_url
    if url.startswith("sqlite:///./"):
        rel_path = url.replace("sqlite:///./", "")
        abs_path = (ROOT_DIR / rel_path).resolve()
        abs_path.parent.mkdir(parents=True, exist_ok=True)
        # Use forward slashes for SQLite URI on Windows
        return f"sqlite:///{abs_path.as_posix()}"
    return url

engine = create_engine(
    get_engine_url(),
    connect_args={"check_same_thread": False} if "sqlite" in settings.database_url else {},
    echo=False
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

class Base(DeclarativeBase):
    pass

def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
