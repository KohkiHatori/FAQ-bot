"""
Pending changes management for vector cache updates.
"""

import json
import os
from typing import Dict, List, Optional, Any, Set
from datetime import datetime
from enum import Enum
from core.config import settings
from core.exceptions import CacheError


class ChangeType(str, Enum):
    """Types of pending changes."""

    CREATED = "created"
    UPDATED = "updated"
    DELETED = "deleted"


class PendingChange:
    """Represents a pending change to be processed during cache rebuild."""

    def __init__(
        self,
        faq_id: int,
        change_type: ChangeType,
        original_status: Optional[str] = None,
        timestamp: Optional[str] = None,
    ):
        self.faq_id = faq_id
        self.change_type = change_type
        self.original_status = original_status
        self.timestamp = timestamp or datetime.now().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "faq_id": self.faq_id,
            "change_type": self.change_type,
            "original_status": self.original_status,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PendingChange":
        """Create from dictionary."""
        return cls(
            faq_id=data["faq_id"],
            change_type=ChangeType(data["change_type"]),
            original_status=data.get("original_status"),
            timestamp=data.get("timestamp"),
        )


class PendingChangesManager:
    """Manages pending changes for vector cache updates."""

    def __init__(self, cache_dir: str = None):
        self.cache_dir = cache_dir or settings.rag_cache_dir
        self.pending_file = os.path.join(self.cache_dir, "pending_changes.json")

        # Ensure cache directory exists
        os.makedirs(self.cache_dir, exist_ok=True)

    def add_pending_change(
        self,
        faq_id: int,
        change_type: ChangeType,
        original_status: Optional[str] = None,
    ) -> None:
        """Add a pending change."""
        try:
            pending_changes = self._load_pending_changes()

            # Remove any existing change for this FAQ (replace with new one)
            pending_changes = {
                faq_id_key: change
                for faq_id_key, change in pending_changes.items()
                if faq_id_key != str(faq_id)
            }

            # Add new change
            change = PendingChange(faq_id, change_type, original_status)
            pending_changes[str(faq_id)] = change.to_dict()

            self._save_pending_changes(pending_changes)

        except Exception as e:
            raise CacheError(f"Failed to add pending change: {e}")

    def remove_pending_change(self, faq_id: int) -> bool:
        """Remove a pending change. Returns True if change was found and removed."""
        try:
            pending_changes = self._load_pending_changes()

            if str(faq_id) in pending_changes:
                del pending_changes[str(faq_id)]
                self._save_pending_changes(pending_changes)
                return True

            return False

        except Exception as e:
            raise CacheError(f"Failed to remove pending change: {e}")

    def get_pending_changes(self) -> Dict[str, Any]:
        """Get all pending changes with summary statistics."""
        try:
            pending_changes = self._load_pending_changes()

            # Convert to list of changes with proper types
            changes = []
            stats = {"created": 0, "updated": 0, "deleted": 0}

            for faq_id_str, change_data in pending_changes.items():
                change = PendingChange.from_dict(change_data)
                changes.append(
                    {
                        "faq_id": change.faq_id,
                        "change_type": change.change_type,
                        "original_status": change.original_status,
                        "timestamp": change.timestamp,
                    }
                )
                stats[change.change_type] += 1

            # Sort by timestamp (newest first)
            changes.sort(key=lambda x: x["timestamp"], reverse=True)

            return {
                "changes": changes,
                "total_count": len(changes),
                "stats": stats,
                "has_pending": len(changes) > 0,
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            raise CacheError(f"Failed to get pending changes: {e}")

    def get_pending_faq_ids(self) -> Set[int]:
        """Get set of FAQ IDs that have pending changes."""
        try:
            pending_changes = self._load_pending_changes()
            return {int(faq_id) for faq_id in pending_changes.keys()}
        except Exception as e:
            raise CacheError(f"Failed to get pending FAQ IDs: {e}")

    def clear_all_pending_changes(self) -> Dict[str, Any]:
        """Clear all pending changes (used after successful cache rebuild)."""
        try:
            pending_changes = self._load_pending_changes()
            count = len(pending_changes)

            # Clear the file
            self._save_pending_changes({})

            return {"cleared_count": count, "timestamp": datetime.now().isoformat()}

        except Exception as e:
            raise CacheError(f"Failed to clear pending changes: {e}")

    def get_changes_for_rebuild(self) -> List[PendingChange]:
        """Get pending changes formatted for cache rebuild processing."""
        try:
            pending_changes = self._load_pending_changes()

            changes = []
            for change_data in pending_changes.values():
                changes.append(PendingChange.from_dict(change_data))

            # Sort by timestamp (oldest first for processing)
            changes.sort(key=lambda x: x.timestamp)

            return changes

        except Exception as e:
            raise CacheError(f"Failed to get changes for rebuild: {e}")

    def _load_pending_changes(self) -> Dict[str, Dict[str, Any]]:
        """Load pending changes from JSON file."""
        if not os.path.exists(self.pending_file):
            return {}

        try:
            with open(self.pending_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            # If file is corrupted, start fresh
            print(f"Warning: Corrupted pending changes file, starting fresh: {e}")
            return {}

    def _save_pending_changes(self, changes: Dict[str, Dict[str, Any]]) -> None:
        """Save pending changes to JSON file."""
        try:
            with open(self.pending_file, "w", encoding="utf-8") as f:
                json.dump(changes, f, indent=2, ensure_ascii=False)
        except IOError as e:
            raise CacheError(f"Failed to save pending changes: {e}")

    def get_file_path(self) -> str:
        """Get the path to the pending changes file."""
        return self.pending_file

    def file_exists(self) -> bool:
        """Check if pending changes file exists."""
        return os.path.exists(self.pending_file)
