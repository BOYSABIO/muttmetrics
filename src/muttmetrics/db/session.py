"""SQLAlchemy engine and session factory"""

from collections.abc import Generator
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from muttmetrics.config import get_settings

_engine = None
_session_factory = None


def get_engine():
    """Create (once) an Engine from DATABASE_URL"""
    global _engine
    if _engine is None:
        _engine = create_engine(get_settings().database_url)
    return _engine


def get_session_factory():
    """Create (once) a sessionmaker bound to the Engine"""
    global _session_factory
    if _session_factory is None:
        _session_factory = sessionmaker(bind=get_engine())
    return _session_factory


@contextmanager
def session_scope() -> Generator[Session]:
    """Yield a Session; commit on success, rollback on error, always close"""
    session = get_session_factory()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
