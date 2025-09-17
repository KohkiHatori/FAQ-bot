"""
Database connection and transaction management.
"""

import sqlite3
import threading
from contextlib import contextmanager
from typing import Generator, Optional
from .config import settings
from .exceptions import DatabaseError


class DatabaseManager:
    """Manages database connections and transactions."""

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or settings.database_path
        self._local = threading.local()

    @contextmanager
    def get_connection(self) -> Generator[sqlite3.Connection, None, None]:
        """Get a database connection with automatic cleanup."""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row  # Enable dict-like access
            yield conn
        except Exception as e:
            if conn:
                conn.rollback()
            raise DatabaseError(f"Database operation failed: {e}")
        finally:
            if conn:
                conn.close()

    @contextmanager
    def get_transaction(self) -> Generator[sqlite3.Connection, None, None]:
        """Get a database connection with automatic transaction handling."""
        with self.get_connection() as conn:
            try:
                yield conn
                conn.commit()
            except Exception as e:
                conn.rollback()
                raise DatabaseError(f"Transaction failed: {e}")

    def execute_query(self, query: str, params: tuple = ()) -> list:
        """Execute a SELECT query and return results."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return cursor.fetchall()

    def execute_one(self, query: str, params: tuple = ()) -> Optional[sqlite3.Row]:
        """Execute a SELECT query and return one result."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return cursor.fetchone()

    def execute_update(self, query: str, params: tuple = ()) -> int:
        """Execute an INSERT/UPDATE/DELETE query and return affected rows."""
        with self.get_transaction() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return cursor.rowcount

    def execute_insert(self, query: str, params: tuple = ()) -> int:
        """Execute an INSERT query and return the last row ID."""
        with self.get_transaction() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return cursor.lastrowid

    def initialize_schema(self):
        """Initialize the database schema."""
        with self.get_transaction() as conn:
            cursor = conn.cursor()

            # Create FAQs table
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS faqs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    question TEXT NOT NULL,
                    answer TEXT NOT NULL,
                    status TEXT DEFAULT 'public',
                    category TEXT DEFAULT 'other',
                    tags TEXT DEFAULT '',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """
            )

            # Create indexes
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_question ON faqs(question)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_answer ON faqs(answer)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_status ON faqs(status)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_category ON faqs(category)")

            # Create FTS table
            cursor.execute(
                """
                CREATE VIRTUAL TABLE IF NOT EXISTS faqs_fts USING fts5(
                    question, answer, content='faqs', content_rowid='id'
                )
            """
            )

            # Create triggers
            cursor.execute(
                """
                CREATE TRIGGER IF NOT EXISTS faqs_ai AFTER INSERT ON faqs BEGIN
                    INSERT INTO faqs_fts(rowid, question, answer)
                    VALUES (new.id, new.question, new.answer);
                END
            """
            )

            cursor.execute(
                """
                CREATE TRIGGER IF NOT EXISTS faqs_ad AFTER DELETE ON faqs BEGIN
                    INSERT INTO faqs_fts(faqs_fts, rowid, question, answer)
                    VALUES('delete', old.id, old.question, old.answer);
                END
            """
            )

            cursor.execute(
                """
                CREATE TRIGGER IF NOT EXISTS faqs_au AFTER UPDATE ON faqs BEGIN
                    INSERT INTO faqs_fts(faqs_fts, rowid, question, answer)
                    VALUES('delete', old.id, old.question, old.answer);
                    INSERT INTO faqs_fts(rowid, question, answer)
                    VALUES (new.id, new.question, new.answer);
                END
            """
            )


# Global database manager instance
db_manager = DatabaseManager()
