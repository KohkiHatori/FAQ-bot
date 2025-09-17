"""
Tests for DatabaseManager functionality.
"""

import pytest
import sqlite3
import tempfile
import os
from unittest.mock import Mock, patch, MagicMock
from contextlib import contextmanager
from core.database import DatabaseManager, db_manager
from core.exceptions import DatabaseError


class TestDatabaseManager:
    """Test the DatabaseManager class."""

    def setup_method(self):
        """Set up test environment for each test."""
        # Create a temporary database file for testing
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        self.temp_db.close()
        self.db_path = self.temp_db.name
        self.db_manager = DatabaseManager(self.db_path)

    def teardown_method(self):
        """Clean up after each test."""
        # Remove the temporary database file
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)

    def test_initialization_with_custom_path(self):
        """Test DatabaseManager initialization with custom path."""
        assert self.db_manager.db_path == self.db_path
        assert hasattr(self.db_manager, "_local")

    def test_initialization_with_default_path(self):
        """Test DatabaseManager initialization with default settings."""
        with patch("core.database.settings") as mock_settings:
            mock_settings.database_path = "/default/path/db.sqlite"

            db = DatabaseManager()

            assert db.db_path == "/default/path/db.sqlite"

    def test_get_connection_success(self):
        """Test successful database connection."""
        with self.db_manager.get_connection() as conn:
            assert isinstance(conn, sqlite3.Connection)
            assert conn.row_factory == sqlite3.Row

            # Test that connection works
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            assert result[0] == 1

    def test_get_connection_cleanup_on_success(self):
        """Test that connection is properly closed after successful use."""
        conn_ref = None

        with self.db_manager.get_connection() as conn:
            conn_ref = conn
            # Test that connection works while in context
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            assert result[0] == 1

        # Connection should be closed after context exit
        # SQLite connections don't have a closed property,
        # but we can test by trying to use it
        with pytest.raises(sqlite3.ProgrammingError):
            conn_ref.execute("SELECT 1")

    def test_get_connection_rollback_on_exception(self):
        """Test that connection is rolled back on exception."""
        with patch("sqlite3.connect") as mock_connect:
            mock_conn = Mock()
            mock_connect.return_value = mock_conn
            mock_conn.cursor.side_effect = Exception("Test error")

            with pytest.raises(DatabaseError, match="Database operation failed"):
                with self.db_manager.get_connection() as conn:
                    conn.cursor()

            mock_conn.rollback.assert_called_once()
            mock_conn.close.assert_called_once()

    def test_get_transaction_success(self):
        """Test successful transaction handling."""
        # Initialize schema first
        self.db_manager.initialize_schema()

        with self.db_manager.get_transaction() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO faqs (question, answer) VALUES (?, ?)",
                ("Test question", "Test answer"),
            )

        # Verify the data was committed
        with self.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM faqs")
            count = cursor.fetchone()[0]
            assert count == 1

    def test_get_transaction_rollback_on_exception(self):
        """Test that transaction is rolled back on exception."""
        # Initialize schema first
        self.db_manager.initialize_schema()

        with pytest.raises(DatabaseError, match="Transaction failed"):
            with self.db_manager.get_transaction() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO faqs (question, answer) VALUES (?, ?)",
                    ("Test question", "Test answer"),
                )
                # Force an error
                cursor.execute("INVALID SQL")

        # Verify the data was rolled back
        with self.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM faqs")
            count = cursor.fetchone()[0]
            assert count == 0

    def test_execute_query_success(self):
        """Test successful query execution."""
        # Initialize schema and add test data
        self.db_manager.initialize_schema()
        with self.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO faqs (question, answer) VALUES (?, ?)", ("Q1", "A1")
            )
            cursor.execute(
                "INSERT INTO faqs (question, answer) VALUES (?, ?)", ("Q2", "A2")
            )
            conn.commit()

        # Test query
        results = self.db_manager.execute_query(
            "SELECT question, answer FROM faqs ORDER BY id"
        )

        assert len(results) == 2
        assert results[0]["question"] == "Q1"
        assert results[0]["answer"] == "A1"
        assert results[1]["question"] == "Q2"
        assert results[1]["answer"] == "A2"

    def test_execute_query_with_parameters(self):
        """Test query execution with parameters."""
        # Initialize schema and add test data
        self.db_manager.initialize_schema()
        with self.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO faqs (question, answer, status) VALUES (?, ?, ?)",
                ("Q1", "A1", "public"),
            )
            cursor.execute(
                "INSERT INTO faqs (question, answer, status) VALUES (?, ?, ?)",
                ("Q2", "A2", "private"),
            )
            conn.commit()

        # Test parameterized query
        results = self.db_manager.execute_query(
            "SELECT question FROM faqs WHERE status = ?", ("public",)
        )

        assert len(results) == 1
        assert results[0]["question"] == "Q1"

    def test_execute_query_empty_result(self):
        """Test query execution with empty result."""
        self.db_manager.initialize_schema()

        results = self.db_manager.execute_query("SELECT * FROM faqs")

        assert results == []

    def test_execute_query_database_error(self):
        """Test query execution with database error."""
        with pytest.raises(DatabaseError, match="Database operation failed"):
            self.db_manager.execute_query("INVALID SQL QUERY")

    def test_execute_one_success(self):
        """Test successful single row query execution."""
        # Initialize schema and add test data
        self.db_manager.initialize_schema()
        with self.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO faqs (question, answer) VALUES (?, ?)",
                ("Test question", "Test answer"),
            )
            conn.commit()

        # Test single row query
        result = self.db_manager.execute_one(
            "SELECT question, answer FROM faqs LIMIT 1"
        )

        assert result is not None
        assert result["question"] == "Test question"
        assert result["answer"] == "Test answer"

    def test_execute_one_no_result(self):
        """Test single row query with no result."""
        self.db_manager.initialize_schema()

        result = self.db_manager.execute_one("SELECT * FROM faqs WHERE id = 999")

        assert result is None

    def test_execute_one_with_parameters(self):
        """Test single row query execution with parameters."""
        # Initialize schema and add test data
        self.db_manager.initialize_schema()
        with self.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO faqs (question, answer) VALUES (?, ?)", ("Q1", "A1")
            )
            cursor.execute(
                "INSERT INTO faqs (question, answer) VALUES (?, ?)", ("Q2", "A2")
            )
            conn.commit()

        # Test parameterized single row query
        result = self.db_manager.execute_one(
            "SELECT question FROM faqs WHERE answer = ?", ("A2",)
        )

        assert result is not None
        assert result["question"] == "Q2"

    def test_execute_one_database_error(self):
        """Test single row query execution with database error."""
        with pytest.raises(DatabaseError, match="Database operation failed"):
            self.db_manager.execute_one("INVALID SQL QUERY")

    def test_execute_update_success(self):
        """Test successful update execution."""
        # Initialize schema and add test data
        self.db_manager.initialize_schema()
        with self.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO faqs (question, answer) VALUES (?, ?)",
                ("Old question", "Old answer"),
            )
            conn.commit()

        # Test update
        affected_rows = self.db_manager.execute_update(
            "UPDATE faqs SET question = ? WHERE answer = ?",
            ("New question", "Old answer"),
        )

        assert affected_rows == 1

        # Verify update
        result = self.db_manager.execute_one("SELECT question FROM faqs")
        assert result["question"] == "New question"

    def test_execute_update_no_rows_affected(self):
        """Test update execution with no rows affected."""
        self.db_manager.initialize_schema()

        affected_rows = self.db_manager.execute_update(
            "UPDATE faqs SET question = ? WHERE id = 999", ("New question",)
        )

        assert affected_rows == 0

    def test_execute_update_delete(self):
        """Test delete execution."""
        # Initialize schema and add test data
        self.db_manager.initialize_schema()
        with self.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO faqs (question, answer) VALUES (?, ?)", ("Q1", "A1")
            )
            cursor.execute(
                "INSERT INTO faqs (question, answer) VALUES (?, ?)", ("Q2", "A2")
            )
            conn.commit()

        # Test delete
        affected_rows = self.db_manager.execute_update(
            "DELETE FROM faqs WHERE question = ?", ("Q1",)
        )

        assert affected_rows == 1

        # Verify deletion
        remaining = self.db_manager.execute_query("SELECT COUNT(*) as count FROM faqs")
        assert remaining[0]["count"] == 1

    def test_execute_update_database_error(self):
        """Test update execution with database error."""
        with pytest.raises(DatabaseError, match="Transaction failed"):
            self.db_manager.execute_update("INVALID SQL UPDATE")

    def test_execute_insert_success(self):
        """Test successful insert execution."""
        self.db_manager.initialize_schema()

        # Test insert
        last_row_id = self.db_manager.execute_insert(
            "INSERT INTO faqs (question, answer) VALUES (?, ?)",
            ("Test question", "Test answer"),
        )

        assert isinstance(last_row_id, int)
        assert last_row_id > 0

        # Verify insert
        result = self.db_manager.execute_one(
            "SELECT id, question FROM faqs WHERE id = ?", (last_row_id,)
        )
        assert result is not None
        assert result["id"] == last_row_id
        assert result["question"] == "Test question"

    def test_execute_insert_multiple(self):
        """Test multiple insert executions."""
        self.db_manager.initialize_schema()

        # Test multiple inserts
        id1 = self.db_manager.execute_insert(
            "INSERT INTO faqs (question, answer) VALUES (?, ?)", ("Q1", "A1")
        )
        id2 = self.db_manager.execute_insert(
            "INSERT INTO faqs (question, answer) VALUES (?, ?)", ("Q2", "A2")
        )

        assert id2 > id1

        # Verify both inserts
        count = self.db_manager.execute_one("SELECT COUNT(*) as count FROM faqs")
        assert count["count"] == 2

    def test_execute_insert_database_error(self):
        """Test insert execution with database error."""
        with pytest.raises(DatabaseError, match="Transaction failed"):
            self.db_manager.execute_insert("INVALID SQL INSERT")

    def test_initialize_schema_creates_tables(self):
        """Test that schema initialization creates required tables."""
        self.db_manager.initialize_schema()

        # Check that faqs table exists
        result = self.db_manager.execute_one(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='faqs'"
        )
        assert result is not None
        assert result["name"] == "faqs"

        # Check that FTS table exists
        result = self.db_manager.execute_one(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='faqs_fts'"
        )
        assert result is not None
        assert result["name"] == "faqs_fts"

    def test_initialize_schema_creates_indexes(self):
        """Test that schema initialization creates indexes."""
        self.db_manager.initialize_schema()

        # Check that indexes exist
        indexes = self.db_manager.execute_query(
            "SELECT name FROM sqlite_master WHERE type='index' AND name LIKE 'idx_%'"
        )

        index_names = [idx["name"] for idx in indexes]
        assert "idx_question" in index_names
        assert "idx_answer" in index_names
        assert "idx_status" in index_names
        assert "idx_category" in index_names

    def test_initialize_schema_creates_triggers(self):
        """Test that schema initialization creates triggers."""
        self.db_manager.initialize_schema()

        # Check that triggers exist
        triggers = self.db_manager.execute_query(
            "SELECT name FROM sqlite_master WHERE type='trigger'"
        )

        trigger_names = [trigger["name"] for trigger in triggers]
        assert "faqs_ai" in trigger_names  # After insert
        assert "faqs_ad" in trigger_names  # After delete
        assert "faqs_au" in trigger_names  # After update

    def test_initialize_schema_table_structure(self):
        """Test that the faqs table has correct structure."""
        self.db_manager.initialize_schema()

        # Get table info
        columns = self.db_manager.execute_query("PRAGMA table_info(faqs)")

        column_names = [col["name"] for col in columns]
        expected_columns = [
            "id",
            "question",
            "answer",
            "status",
            "category",
            "tags",
            "created_at",
            "updated_at",
        ]

        for expected_col in expected_columns:
            assert expected_col in column_names

    def test_initialize_schema_default_values(self):
        """Test that default values work correctly."""
        self.db_manager.initialize_schema()

        # Insert minimal data
        last_id = self.db_manager.execute_insert(
            "INSERT INTO faqs (question, answer) VALUES (?, ?)",
            ("Test question", "Test answer"),
        )

        # Check defaults
        result = self.db_manager.execute_one(
            "SELECT * FROM faqs WHERE id = ?", (last_id,)
        )

        assert result["status"] == "public"
        assert result["category"] == "other"
        assert result["tags"] == ""
        assert result["created_at"] is not None
        assert result["updated_at"] is not None

    def test_initialize_schema_fts_integration(self):
        """Test that FTS integration works."""
        self.db_manager.initialize_schema()

        # Insert data
        self.db_manager.execute_insert(
            "INSERT INTO faqs (question, answer) VALUES (?, ?)",
            ("How to use Python?", "Python is a programming language"),
        )

        # Test FTS search
        results = self.db_manager.execute_query(
            "SELECT * FROM faqs_fts WHERE faqs_fts MATCH ?", ("Python",)
        )

        assert len(results) == 1
        assert "Python" in results[0]["question"] or "Python" in results[0]["answer"]

    def test_initialize_schema_multiple_calls(self):
        """Test that multiple schema initialization calls are safe."""
        # Should not raise any errors
        self.db_manager.initialize_schema()
        self.db_manager.initialize_schema()
        self.db_manager.initialize_schema()

        # Table should still exist and work
        self.db_manager.execute_insert(
            "INSERT INTO faqs (question, answer) VALUES (?, ?)", ("Test", "Test")
        )

        count = self.db_manager.execute_one("SELECT COUNT(*) as count FROM faqs")
        assert count["count"] == 1

    def test_global_db_manager_instance(self):
        """Test that global db_manager instance exists."""
        assert db_manager is not None
        assert isinstance(db_manager, DatabaseManager)

    def test_threading_local_attribute(self):
        """Test that _local attribute is properly initialized."""
        import threading

        assert isinstance(self.db_manager._local, threading.local)

    def test_connection_context_manager_protocol(self):
        """Test that connection context manager follows protocol."""
        # Test __enter__ and __exit__ methods exist
        cm = self.db_manager.get_connection()
        assert hasattr(cm, "__enter__")
        assert hasattr(cm, "__exit__")

    def test_transaction_context_manager_protocol(self):
        """Test that transaction context manager follows protocol."""
        # Test __enter__ and __exit__ methods exist
        cm = self.db_manager.get_transaction()
        assert hasattr(cm, "__enter__")
        assert hasattr(cm, "__exit__")

    def test_row_factory_dict_access(self):
        """Test that row factory enables dict-like access."""
        self.db_manager.initialize_schema()

        # Insert test data
        self.db_manager.execute_insert(
            "INSERT INTO faqs (question, answer) VALUES (?, ?)",
            ("Test question", "Test answer"),
        )

        # Test dict-like access
        result = self.db_manager.execute_one("SELECT question, answer FROM faqs")

        # Should work with both dict-style and attribute-style access
        assert result["question"] == "Test question"
        assert result["answer"] == "Test answer"

        # Should also work with index access
        assert result[0] == "Test question"
        assert result[1] == "Test answer"

    def test_database_file_creation(self):
        """Test that database file is created when accessed."""
        # Remove the file if it exists
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)

        # Access database - should create the file
        with self.db_manager.get_connection() as conn:
            pass

        assert os.path.exists(self.db_path)

    def test_concurrent_access_safety(self):
        """Test basic concurrent access safety."""
        self.db_manager.initialize_schema()

        # This is a basic test - in real scenarios you'd test with actual threads
        # Multiple consecutive operations should work
        for i in range(5):
            self.db_manager.execute_insert(
                "INSERT INTO faqs (question, answer) VALUES (?, ?)",
                (f"Question {i}", f"Answer {i}"),
            )

        count = self.db_manager.execute_one("SELECT COUNT(*) as count FROM faqs")
        assert count["count"] == 5


if __name__ == "__main__":
    pytest.main([__file__])
