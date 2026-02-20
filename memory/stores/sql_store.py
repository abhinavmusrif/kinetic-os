"""SQLite SQLAlchemy store wrapper."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from memory.schemas import Base


class SQLStore:
    """Provides SQLAlchemy session management for SQLite persistence."""

    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.engine = create_engine(f"sqlite+pysqlite:///{self.db_path}", future=True)
        self._session_factory = sessionmaker(bind=self.engine, future=True)

    def create_all(self) -> None:
        """Create all schema tables if missing."""
        Base.metadata.create_all(self.engine)

    @contextmanager
    def session(self) -> Iterator[Session]:
        """Context manager that commits on success and rolls back on error."""
        sess = self._session_factory()
        try:
            yield sess
            sess.commit()
        except Exception:
            sess.rollback()
            raise
        finally:
            sess.close()
