"""Synchronous SQLAlchemy engine and session lifecycle."""
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from config import settings


engine_options = {
    "echo": settings.DEBUG,
    "pool_pre_ping": True,
}
if "mysql" in settings.database_url:
    engine_options.update(
        pool_size=10,
        max_overflow=20,
        pool_recycle=3600,
        pool_timeout=30,
    )

engine = create_engine(settings.database_url, **engine_options)
db_session = sessionmaker(bind=engine, class_=Session, expire_on_commit=False)
Base = declarative_base()


def get_db():
    """Yield a synchronous session for compatibility with dependency-style callers."""
    with db_session() as session:
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise


@contextmanager
def get_db_context():
    """Provide a transactional synchronous database session."""
    with db_session() as session:
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
