"""
Tests for PendingChanges functionality.
"""

import pytest
import os
import tempfile
import json
from datetime import datetime
from unittest.mock import Mock, patch
from core.pending_changes import PendingChangesManager, PendingChange, ChangeType
from core.exceptions import CacheError


class TestChangeType:
    """Test the ChangeType enum."""

    def test_change_type_values(self):
        """Test ChangeType enum values."""
        assert ChangeType.CREATED == "created"
        assert ChangeType.UPDATED == "updated"
        assert ChangeType.DELETED == "deleted"

    def test_change_type_from_string(self):
        """Test creating ChangeType from string."""
        assert ChangeType("created") == ChangeType.CREATED
        assert ChangeType("updated") == ChangeType.UPDATED
        assert ChangeType("deleted") == ChangeType.DELETED


class TestPendingChange:
    """Test the PendingChange class."""

    def test_initialization_minimal(self):
        """Test PendingChange initialization with minimal parameters."""
        change = PendingChange(faq_id=1, change_type=ChangeType.CREATED)

        assert change.faq_id == 1
        assert change.change_type == ChangeType.CREATED
        assert change.original_status is None
        assert change.timestamp is not None
        assert isinstance(change.timestamp, str)

    def test_initialization_full(self):
        """Test PendingChange initialization with all parameters."""
        timestamp = "2024-01-01T12:00:00"
        change = PendingChange(
            faq_id=1,
            change_type=ChangeType.UPDATED,
            original_status="public",
            timestamp=timestamp,
        )

        assert change.faq_id == 1
        assert change.change_type == ChangeType.UPDATED
        assert change.original_status == "public"
        assert change.timestamp == timestamp

    def test_to_dict(self):
        """Test converting PendingChange to dictionary."""
        timestamp = "2024-01-01T12:00:00"
        change = PendingChange(
            faq_id=1,
            change_type=ChangeType.UPDATED,
            original_status="public",
            timestamp=timestamp,
        )

        expected = {
            "faq_id": 1,
            "change_type": "updated",
            "original_status": "public",
            "timestamp": timestamp,
        }

        assert change.to_dict() == expected

    def test_to_dict_minimal(self):
        """Test converting minimal PendingChange to dictionary."""
        change = PendingChange(faq_id=1, change_type=ChangeType.CREATED)

        result = change.to_dict()

        assert result["faq_id"] == 1
        assert result["change_type"] == "created"
        assert result["original_status"] is None
        assert "timestamp" in result

    def test_from_dict(self):
        """Test creating PendingChange from dictionary."""
        data = {
            "faq_id": 1,
            "change_type": "updated",
            "original_status": "public",
            "timestamp": "2024-01-01T12:00:00",
        }

        change = PendingChange.from_dict(data)

        assert change.faq_id == 1
        assert change.change_type == ChangeType.UPDATED
        assert change.original_status == "public"
        assert change.timestamp == "2024-01-01T12:00:00"

    def test_from_dict_minimal(self):
        """Test creating PendingChange from minimal dictionary."""
        data = {"faq_id": 1, "change_type": "created"}

        change = PendingChange.from_dict(data)

        assert change.faq_id == 1
        assert change.change_type == ChangeType.CREATED
        assert change.original_status is None
        # When timestamp is not provided, it gets set to current time
        assert change.timestamp is not None
        assert isinstance(change.timestamp, str)


class TestPendingChangesManager:
    """Test the PendingChangesManager class."""

    def setup_method(self):
        """Set up test environment for each test."""
        # Create a temporary directory for cache
        self.temp_dir = tempfile.mkdtemp()
        self.manager = PendingChangesManager(cache_dir=self.temp_dir)

    def teardown_method(self):
        """Clean up after each test."""
        # Clean up temp directory
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_initialization(self):
        """Test PendingChangesManager initialization."""
        assert self.manager.cache_dir == self.temp_dir
        assert self.manager.pending_file == os.path.join(
            self.temp_dir, "pending_changes.json"
        )
        assert os.path.exists(self.temp_dir)

    def test_initialization_with_defaults(self):
        """Test PendingChangesManager initialization with default settings."""
        with patch("core.pending_changes.settings") as mock_settings:
            mock_settings.rag_cache_dir = tempfile.mkdtemp()

            manager = PendingChangesManager()

            assert manager.cache_dir == mock_settings.rag_cache_dir

    def test_get_file_path(self):
        """Test get_file_path method."""
        expected_path = os.path.join(self.temp_dir, "pending_changes.json")
        assert self.manager.get_file_path() == expected_path

    def test_file_exists_false_initially(self):
        """Test file_exists returns False initially."""
        assert self.manager.file_exists() is False

    def test_file_exists_true_after_save(self):
        """Test file_exists returns True after saving changes."""
        self.manager.add_pending_change(1, ChangeType.CREATED)
        assert self.manager.file_exists() is True

    def test_add_pending_change(self):
        """Test adding a pending change."""
        self.manager.add_pending_change(1, ChangeType.CREATED, "public")

        # Check file was created
        assert os.path.exists(self.manager.pending_file)

        # Check content
        with open(self.manager.pending_file, "r") as f:
            data = json.load(f)

        assert "1" in data
        assert data["1"]["faq_id"] == 1
        assert data["1"]["change_type"] == "created"
        assert data["1"]["original_status"] == "public"
        assert "timestamp" in data["1"]

    def test_add_pending_change_replaces_existing(self):
        """Test adding a pending change replaces existing one for same FAQ."""
        # Add first change
        self.manager.add_pending_change(1, ChangeType.CREATED, "public")

        # Add second change for same FAQ
        self.manager.add_pending_change(1, ChangeType.UPDATED, "private")

        # Check only the second change exists
        with open(self.manager.pending_file, "r") as f:
            data = json.load(f)

        assert len(data) == 1
        assert data["1"]["change_type"] == "updated"
        assert data["1"]["original_status"] == "private"

    def test_add_pending_change_multiple_faqs(self):
        """Test adding pending changes for multiple FAQs."""
        self.manager.add_pending_change(1, ChangeType.CREATED)
        self.manager.add_pending_change(2, ChangeType.UPDATED)
        self.manager.add_pending_change(3, ChangeType.DELETED)

        with open(self.manager.pending_file, "r") as f:
            data = json.load(f)

        assert len(data) == 3
        assert "1" in data
        assert "2" in data
        assert "3" in data

    def test_add_pending_change_exception_handling(self):
        """Test add_pending_change exception handling."""
        with patch.object(
            self.manager, "_save_pending_changes", side_effect=Exception("Save error")
        ):
            with pytest.raises(CacheError, match="Failed to add pending change"):
                self.manager.add_pending_change(1, ChangeType.CREATED)

    def test_remove_pending_change_existing(self):
        """Test removing an existing pending change."""
        # Add a change first
        self.manager.add_pending_change(1, ChangeType.CREATED)

        # Remove it
        result = self.manager.remove_pending_change(1)

        assert result is True

        # Check it's gone
        with open(self.manager.pending_file, "r") as f:
            data = json.load(f)

        assert len(data) == 0

    def test_remove_pending_change_nonexistent(self):
        """Test removing a non-existent pending change."""
        result = self.manager.remove_pending_change(999)
        assert result is False

    def test_remove_pending_change_with_others(self):
        """Test removing one change while others remain."""
        # Add multiple changes
        self.manager.add_pending_change(1, ChangeType.CREATED)
        self.manager.add_pending_change(2, ChangeType.UPDATED)
        self.manager.add_pending_change(3, ChangeType.DELETED)

        # Remove one
        result = self.manager.remove_pending_change(2)

        assert result is True

        # Check others remain
        with open(self.manager.pending_file, "r") as f:
            data = json.load(f)

        assert len(data) == 2
        assert "1" in data
        assert "3" in data
        assert "2" not in data

    def test_remove_pending_change_exception_handling(self):
        """Test remove_pending_change exception handling."""
        # Add a change first so the removal path is taken
        self.manager.add_pending_change(1, ChangeType.CREATED)

        with patch.object(
            self.manager, "_save_pending_changes", side_effect=Exception("Save error")
        ):
            with pytest.raises(CacheError, match="Failed to remove pending change"):
                self.manager.remove_pending_change(1)

    def test_get_pending_changes_empty(self):
        """Test get_pending_changes with no changes."""
        result = self.manager.get_pending_changes()

        assert result["changes"] == []
        assert result["total_count"] == 0
        assert result["stats"] == {"created": 0, "updated": 0, "deleted": 0}
        assert result["has_pending"] is False
        assert "timestamp" in result

    def test_get_pending_changes_with_data(self):
        """Test get_pending_changes with data."""
        # Add changes with specific timestamps for predictable sorting
        self.manager.add_pending_change(1, ChangeType.CREATED, "public")
        self.manager.add_pending_change(2, ChangeType.UPDATED, "private")
        self.manager.add_pending_change(3, ChangeType.DELETED)

        result = self.manager.get_pending_changes()

        assert result["total_count"] == 3
        assert result["stats"]["created"] == 1
        assert result["stats"]["updated"] == 1
        assert result["stats"]["deleted"] == 1
        assert result["has_pending"] is True

        # Check changes structure
        changes = result["changes"]
        assert len(changes) == 3

        # All changes should have required fields
        for change in changes:
            assert "faq_id" in change
            assert "change_type" in change
            assert "timestamp" in change
            assert "original_status" in change

    def test_get_pending_changes_sorting(self):
        """Test get_pending_changes sorts by timestamp (newest first)."""
        # Add changes with specific timestamps
        timestamp1 = "2024-01-01T10:00:00"
        timestamp2 = "2024-01-01T12:00:00"
        timestamp3 = "2024-01-01T11:00:00"

        # Manually create changes with specific timestamps
        changes_data = {
            "1": {
                "faq_id": 1,
                "change_type": "created",
                "original_status": None,
                "timestamp": timestamp1,
            },
            "2": {
                "faq_id": 2,
                "change_type": "updated",
                "original_status": None,
                "timestamp": timestamp2,
            },
            "3": {
                "faq_id": 3,
                "change_type": "deleted",
                "original_status": None,
                "timestamp": timestamp3,
            },
        }

        self.manager._save_pending_changes(changes_data)

        result = self.manager.get_pending_changes()
        changes = result["changes"]

        # Should be sorted by timestamp, newest first
        assert changes[0]["timestamp"] == timestamp2  # 12:00
        assert changes[1]["timestamp"] == timestamp3  # 11:00
        assert changes[2]["timestamp"] == timestamp1  # 10:00

    def test_get_pending_changes_exception_handling(self):
        """Test get_pending_changes exception handling."""
        with patch.object(
            self.manager, "_load_pending_changes", side_effect=Exception("Load error")
        ):
            with pytest.raises(CacheError, match="Failed to get pending changes"):
                self.manager.get_pending_changes()

    def test_get_pending_faq_ids_empty(self):
        """Test get_pending_faq_ids with no changes."""
        result = self.manager.get_pending_faq_ids()
        assert result == set()

    def test_get_pending_faq_ids_with_data(self):
        """Test get_pending_faq_ids with data."""
        self.manager.add_pending_change(1, ChangeType.CREATED)
        self.manager.add_pending_change(2, ChangeType.UPDATED)
        self.manager.add_pending_change(3, ChangeType.DELETED)

        result = self.manager.get_pending_faq_ids()
        assert result == {1, 2, 3}

    def test_get_pending_faq_ids_exception_handling(self):
        """Test get_pending_faq_ids exception handling."""
        with patch.object(
            self.manager, "_load_pending_changes", side_effect=Exception("Load error")
        ):
            with pytest.raises(CacheError, match="Failed to get pending FAQ IDs"):
                self.manager.get_pending_faq_ids()

    def test_clear_all_pending_changes_empty(self):
        """Test clearing pending changes when none exist."""
        result = self.manager.clear_all_pending_changes()

        assert result["cleared_count"] == 0
        assert "timestamp" in result

    def test_clear_all_pending_changes_with_data(self):
        """Test clearing pending changes with data."""
        # Add some changes
        self.manager.add_pending_change(1, ChangeType.CREATED)
        self.manager.add_pending_change(2, ChangeType.UPDATED)

        result = self.manager.clear_all_pending_changes()

        assert result["cleared_count"] == 2
        assert "timestamp" in result

        # Check file is empty
        with open(self.manager.pending_file, "r") as f:
            data = json.load(f)

        assert len(data) == 0

    def test_clear_all_pending_changes_exception_handling(self):
        """Test clear_all_pending_changes exception handling."""
        with patch.object(
            self.manager, "_save_pending_changes", side_effect=Exception("Save error")
        ):
            with pytest.raises(CacheError, match="Failed to clear pending changes"):
                self.manager.clear_all_pending_changes()

    def test_get_changes_for_rebuild_empty(self):
        """Test get_changes_for_rebuild with no changes."""
        result = self.manager.get_changes_for_rebuild()
        assert result == []

    def test_get_changes_for_rebuild_with_data(self):
        """Test get_changes_for_rebuild with data."""
        # Add changes with specific timestamps
        timestamp1 = "2024-01-01T12:00:00"
        timestamp2 = "2024-01-01T10:00:00"
        timestamp3 = "2024-01-01T11:00:00"

        changes_data = {
            "1": {
                "faq_id": 1,
                "change_type": "created",
                "original_status": None,
                "timestamp": timestamp1,
            },
            "2": {
                "faq_id": 2,
                "change_type": "updated",
                "original_status": None,
                "timestamp": timestamp2,
            },
            "3": {
                "faq_id": 3,
                "change_type": "deleted",
                "original_status": None,
                "timestamp": timestamp3,
            },
        }

        self.manager._save_pending_changes(changes_data)

        result = self.manager.get_changes_for_rebuild()

        assert len(result) == 3
        assert all(isinstance(change, PendingChange) for change in result)

        # Should be sorted by timestamp, oldest first for processing
        assert result[0].timestamp == timestamp2  # 10:00
        assert result[1].timestamp == timestamp3  # 11:00
        assert result[2].timestamp == timestamp1  # 12:00

    def test_get_changes_for_rebuild_exception_handling(self):
        """Test get_changes_for_rebuild exception handling."""
        with patch.object(
            self.manager, "_load_pending_changes", side_effect=Exception("Load error")
        ):
            with pytest.raises(CacheError, match="Failed to get changes for rebuild"):
                self.manager.get_changes_for_rebuild()

    def test_load_pending_changes_no_file(self):
        """Test _load_pending_changes when file doesn't exist."""
        result = self.manager._load_pending_changes()
        assert result == {}

    def test_load_pending_changes_valid_file(self):
        """Test _load_pending_changes with valid file."""
        # Create a valid file
        test_data = {
            "1": {
                "faq_id": 1,
                "change_type": "created",
                "original_status": None,
                "timestamp": "2024-01-01T12:00:00",
            }
        }

        with open(self.manager.pending_file, "w") as f:
            json.dump(test_data, f)

        result = self.manager._load_pending_changes()
        assert result == test_data

    def test_load_pending_changes_corrupted_file(self):
        """Test _load_pending_changes with corrupted file."""
        # Create a corrupted file
        with open(self.manager.pending_file, "w") as f:
            f.write("invalid json")

        with patch("builtins.print") as mock_print:
            result = self.manager._load_pending_changes()

        assert result == {}
        mock_print.assert_called_once()
        assert "Warning: Corrupted pending changes file" in mock_print.call_args[0][0]

    def test_save_pending_changes(self):
        """Test _save_pending_changes."""
        test_data = {
            "1": {
                "faq_id": 1,
                "change_type": "created",
                "original_status": None,
                "timestamp": "2024-01-01T12:00:00",
            }
        }

        self.manager._save_pending_changes(test_data)

        # Check file was created with correct content
        assert os.path.exists(self.manager.pending_file)

        with open(self.manager.pending_file, "r") as f:
            saved_data = json.load(f)

        assert saved_data == test_data

    def test_save_pending_changes_exception_handling(self):
        """Test _save_pending_changes exception handling."""
        # Make directory read-only to cause write error
        os.chmod(self.temp_dir, 0o444)

        try:
            with pytest.raises(CacheError, match="Failed to save pending changes"):
                self.manager._save_pending_changes({})
        finally:
            # Restore permissions for cleanup
            os.chmod(self.temp_dir, 0o755)

    def test_unicode_handling(self):
        """Test handling of unicode characters in pending changes."""
        # Add change with unicode characters
        self.manager.add_pending_change(1, ChangeType.CREATED, "公開")

        # Load and check
        result = self.manager.get_pending_changes()

        assert len(result["changes"]) == 1
        assert result["changes"][0]["original_status"] == "公開"

    def test_large_faq_id(self):
        """Test handling of large FAQ IDs."""
        large_id = 999999999
        self.manager.add_pending_change(large_id, ChangeType.CREATED)

        result = self.manager.get_pending_faq_ids()
        assert large_id in result


if __name__ == "__main__":
    pytest.main([__file__])
