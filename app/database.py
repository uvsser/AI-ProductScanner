# Compatibility bridge for existing database imports
from app.infrastructure.database.session import Base, engine, SessionLocal, get_db

__all__ = ["Base", "engine", "SessionLocal", "get_db"]
