"""
FAQ management with combined data access and business logic.
"""

import json
from typing import Dict, List, Optional, Any
from datetime import datetime
from core.database import DatabaseManager
from core.config import settings
from core.exceptions import ValidationError, NotFoundError, DatabaseError
from core.pending_changes import PendingChangesManager, ChangeType
from models import FAQResponse, FAQCreateRequest, FAQUpdateRequest


class FAQManager:
    """Combined FAQ repository and service with data access and business logic."""

    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
        self.pending_changes = PendingChangesManager()

    # Public API Methods (Business Logic)

    def get_faq_by_id(self, faq_id: int) -> FAQResponse:
        """Get FAQ by ID."""
        faq = self._get_by_id(faq_id)
        if not faq:
            raise NotFoundError(f"FAQ not found with ID: {faq_id}")
        return faq

    def get_faqs(
        self,
        limit: int = 50,
        offset: int = 0,
        status: Optional[str] = None,
        category: Optional[str] = None,
        tag: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get FAQs with pagination and filtering."""
        # Validate parameters
        if limit <= 0 or limit > 500:
            raise ValidationError("Limit must be between 1 and 500")
        if offset < 0:
            raise ValidationError("Offset cannot be negative")

        faqs, total_count = self._get_all(
            limit=limit, offset=offset, status=status, category=category, tag=tag
        )

        has_more = (offset + len(faqs)) < total_count

        return {
            "faqs": faqs,
            "total": total_count,
            "limit": limit,
            "offset": offset,
            "has_more": has_more,
            "timestamp": datetime.now().isoformat(),
        }

    def create_faq(self, request: FAQCreateRequest) -> FAQResponse:
        """Create a new FAQ with validation."""
        # Validate input
        self._validate_faq_input(request.question, request.answer)
        self._validate_status(request.status)
        self._validate_tags(request.tags)

        # Store original status for pending changes
        original_status = request.status

        # Create FAQ with "pending" status to indicate it needs vector embedding
        faq = self._create(
            question=request.question.strip(),
            answer=request.answer.strip(),
            status="pending",  # Always set to pending initially
            category=request.category,
            tags=request.tags,
        )

        # Track pending change with original status
        self.pending_changes.add_pending_change(
            faq_id=faq.id,
            change_type=ChangeType.CREATED,
            original_status=original_status,
        )

        return faq

    def update_faq(
        self, faq_id: int, request: FAQUpdateRequest
    ) -> tuple[FAQResponse, FAQResponse]:
        """Update an existing FAQ."""
        # Get existing FAQ
        old_faq = self.get_faq_by_id(faq_id)

        # Validate updates
        updates = {}
        original_status = old_faq.status  # Store original status

        if request.question is not None:
            self._validate_question(request.question)
            updates["question"] = request.question.strip()

        if request.answer is not None:
            self._validate_answer(request.answer)
            updates["answer"] = request.answer.strip()

        if request.status is not None:
            self._validate_status(request.status)
            # Store the intended status, but we'll set to pending for now
            original_status = request.status

        if request.category is not None:
            updates["category"] = request.category

        if request.tags is not None:
            self._validate_tags(request.tags)
            updates["tags"] = request.tags

        # Always set status to pending to indicate it needs re-embedding
        updates["status"] = "pending"

        # Update FAQ
        updated_faq = self._update(faq_id, **updates)
        if not updated_faq:
            raise NotFoundError(f"FAQ not found with ID: {faq_id}")

        # Track pending change with original/intended status
        self.pending_changes.add_pending_change(
            faq_id=faq_id,
            change_type=ChangeType.UPDATED,
            original_status=original_status,
        )

        return updated_faq, old_faq

    def delete_faq(self, faq_id: int) -> FAQResponse:
        """Delete an FAQ."""
        # Get existing FAQ to store its status
        existing_faq = self.get_faq_by_id(faq_id)

        # Delete the FAQ
        deleted_faq = self._delete(faq_id)

        # Track pending change (for cleanup during cache rebuild)
        self.pending_changes.add_pending_change(
            faq_id=faq_id,
            change_type=ChangeType.DELETED,
            original_status=existing_faq.status,
        )

        return deleted_faq

    def search_faqs(self, query: str, limit: int = 20) -> List[FAQResponse]:
        """Search FAQs."""
        if not query.strip():
            raise ValidationError("Search query cannot be empty")

        if limit <= 0 or limit > 50:
            raise ValidationError("Search limit must be between 1 and 50")

        return self._search(query.strip(), limit)

    def get_all_tags(self) -> Dict[str, Any]:
        """Get all unique tags."""
        tags = self._get_all_tags()
        return {
            "tags": tags,
            "count": len(tags),
            "timestamp": datetime.now().isoformat(),
        }

    def get_all_categories(self) -> Dict[str, Any]:
        """Get all unique categories."""
        categories = self._get_all_categories()
        return {
            "categories": categories,
            "total_categories": len(categories),
            "timestamp": datetime.now().isoformat(),
        }

    def get_statistics(self) -> Dict[str, Any]:
        """Get FAQ statistics."""
        stats = self._get_statistics()
        stats["timestamp"] = datetime.now().isoformat()
        return stats

    def load_faqs_for_rag(self) -> List[Dict[str, Any]]:
        """Load FAQ data for RAG system."""
        return self._load_for_rag()

    def get_pending_changes(self) -> Dict[str, Any]:
        """Get pending changes information."""
        return self.pending_changes.get_pending_changes()

    def restore_faq_statuses_after_rebuild(self) -> Dict[str, Any]:
        """Restore FAQ statuses to their intended values after cache rebuild."""
        try:
            changes = self.pending_changes.get_changes_for_rebuild()
            restored_count = 0

            for change in changes:
                if change.change_type == ChangeType.DELETED:
                    # Skip deleted FAQs - they're already gone
                    continue

                # Restore the FAQ status to its original/intended value
                if change.original_status and change.original_status != "pending":
                    self._update_status_only(change.faq_id, change.original_status)
                    restored_count += 1

            # Clear all pending changes after successful restore
            clear_result = self.pending_changes.clear_all_pending_changes()

            return {
                "success": True,
                "restored_count": restored_count,
                "cleared_count": clear_result["cleared_count"],
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            raise DatabaseError(f"Failed to restore FAQ statuses: {e}")

    def _update_status_only(self, faq_id: int, status: str) -> None:
        """Update only the status of an FAQ (internal method)."""
        query = "UPDATE faqs SET status = ?, updated_at = ? WHERE id = ?"
        params = (status, datetime.now().isoformat(), faq_id)
        self.db.execute_query(query, params)

    # Private Data Access Methods (Repository Layer)

    def _get_by_id(self, faq_id: int) -> Optional[FAQResponse]:
        """Get FAQ by ID."""
        query = """
            SELECT id, question, answer, status, category, tags, created_at, updated_at
            FROM faqs WHERE id = ?
        """
        row = self.db.execute_one(query, (faq_id,))
        return self._row_to_faq(row) if row else None

    def _get_all(
        self,
        limit: Optional[int] = None,
        offset: int = 0,
        status: Optional[str] = None,
        category: Optional[str] = None,
        tag: Optional[str] = None,
    ) -> tuple[List[FAQResponse], int]:
        """Get all FAQs with optional filtering and pagination."""
        filters = {"status": status, "category": category, "tag": tag}
        where_clause, params = self._build_where_clause(filters)

        # Get total count
        count_query = f"SELECT COUNT(*) FROM faqs{where_clause}"
        total_count = self.db.execute_one(count_query, params)[0]

        # Get FAQs with pagination
        query = f"""
            SELECT id, question, answer, status, category, tags, created_at, updated_at
            FROM faqs{where_clause} ORDER BY id
        """
        query = self._apply_pagination(query, limit, offset)

        rows = self.db.execute_query(query, params)
        faqs = [self._row_to_faq(row) for row in rows]

        return faqs, total_count

    def _create(
        self,
        question: str,
        answer: str,
        status: str = "public",
        category: str = "other",
        tags: List[str] = None,
    ) -> FAQResponse:
        """Create a new FAQ."""
        tags = tags or []
        tags_json = self._serialize_tags(tags)

        query = """
            INSERT INTO faqs (question, answer, status, category, tags)
            VALUES (?, ?, ?, ?, ?)
        """
        faq_id = self.db.execute_insert(
            query, (question, answer, status, category, tags_json)
        )

        # Return the created FAQ
        created_faq = self._get_by_id(faq_id)
        if not created_faq:
            raise DatabaseError("Failed to retrieve created FAQ")
        return created_faq

    def _update(self, faq_id: int, **updates) -> Optional[FAQResponse]:
        """Update an existing FAQ."""
        if not updates:
            return self._get_by_id(faq_id)

        # Get existing FAQ first
        existing = self._get_by_id(faq_id)
        if not existing:
            raise NotFoundError(f"FAQ not found with ID: {faq_id}")

        # Build update query
        set_clauses = []
        params = []

        for field, value in updates.items():
            if field == "tags" and isinstance(value, list):
                set_clauses.append("tags = ?")
                params.append(self._serialize_tags(value))
            elif field in ["question", "answer", "status", "category"]:
                set_clauses.append(f"{field} = ?")
                params.append(value)

        if set_clauses:
            set_clauses.append("updated_at = CURRENT_TIMESTAMP")
            params.append(faq_id)

            query = f"UPDATE faqs SET {', '.join(set_clauses)} WHERE id = ?"
            self.db.execute_update(query, tuple(params))

        return self._get_by_id(faq_id)

    def _delete(self, faq_id: int) -> Optional[FAQResponse]:
        """Delete an FAQ and return the deleted FAQ."""
        # Get FAQ before deletion
        faq = self._get_by_id(faq_id)
        if not faq:
            raise NotFoundError(f"FAQ not found with ID: {faq_id}")

        query = "DELETE FROM faqs WHERE id = ?"
        rows_affected = self.db.execute_update(query, (faq_id,))

        if rows_affected == 0:
            raise DatabaseError("Failed to delete FAQ")

        return faq

    def _search(self, query_text: str, limit: int = 20) -> List[FAQResponse]:
        """Search FAQs using LIKE-based search."""
        query = """
            SELECT * FROM (
                SELECT id, question, answer, status, category, tags,
                       created_at, updated_at,
                       CASE
                           WHEN question LIKE ? THEN 10.0
                           WHEN answer LIKE ? THEN 8.0
                           WHEN category LIKE ? THEN 7.0
                           WHEN (tags != '' AND tags != '[]' AND tags LIKE ?) THEN 6.0
                           WHEN question LIKE ? THEN 5.0
                           WHEN answer LIKE ? THEN 3.0
                           ELSE 0.0
                       END as score
                FROM faqs
                WHERE question LIKE ? OR answer LIKE ? OR category LIKE ?
                   OR (tags != '' AND tags != '[]' AND tags LIKE ?)
            ) WHERE score > 0
            ORDER BY score DESC, id ASC
            LIMIT ?
        """

        search_term = f"%{query_text}%"
        tag_term = f'%"{query_text}"%'

        params = (
            search_term,
            search_term,
            search_term,
            tag_term,  # exact matches
            search_term,
            search_term,  # partial matches
            search_term,
            search_term,
            search_term,
            tag_term,  # where clause
            limit,
        )

        rows = self.db.execute_query(query, params)
        return [self._row_to_faq(row) for row in rows]

    def _get_all_tags(self) -> List[str]:
        """Get all unique tags from the database."""
        query = "SELECT tags FROM faqs WHERE tags != '' AND tags != '[]'"
        rows = self.db.execute_query(query)

        all_tags = set()
        for row in rows:
            tags = self._parse_tags(row[0])
            all_tags.update(tags)

        return sorted(list(all_tags))

    def _get_all_categories(self) -> List[Dict[str, Any]]:
        """Get all unique categories with their counts."""
        query = """
            SELECT category, COUNT(*) as count
            FROM faqs
            WHERE category != ''
            GROUP BY category
            ORDER BY category
        """
        rows = self.db.execute_query(query)
        return [{"name": row[0], "count": row[1]} for row in rows]

    def _get_statistics(self) -> Dict[str, Any]:
        """Get comprehensive FAQ statistics."""
        stats = {}

        # Basic counts
        stats["total_faqs"] = self.db.execute_one("SELECT COUNT(*) FROM faqs")[0]
        stats["public_faqs"] = self.db.execute_one(
            "SELECT COUNT(*) FROM faqs WHERE status = 'public'"
        )[0]
        stats["private_faqs"] = self.db.execute_one(
            "SELECT COUNT(*) FROM faqs WHERE status = 'private'"
        )[0]

        # Recent FAQs (last 7 days)
        stats["recent_faqs"] = self.db.execute_one(
            "SELECT COUNT(*) FROM faqs WHERE created_at >= datetime('now', '-7 days')"
        )[0]

        # Text length statistics
        stats["avg_question_length"] = (
            self.db.execute_one("SELECT AVG(LENGTH(question)) FROM faqs")[0] or 0
        )
        stats["avg_answer_length"] = (
            self.db.execute_one("SELECT AVG(LENGTH(answer)) FROM faqs")[0] or 0
        )
        stats["max_question_length"] = (
            self.db.execute_one("SELECT MAX(LENGTH(question)) FROM faqs")[0] or 0
        )
        stats["max_answer_length"] = (
            self.db.execute_one("SELECT MAX(LENGTH(answer)) FROM faqs")[0] or 0
        )

        # FAQs with tags
        stats["faqs_with_tags"] = self.db.execute_one(
            "SELECT COUNT(*) FROM faqs WHERE tags != '' AND tags != '[]'"
        )[0]

        return stats

    def _load_for_rag(self) -> List[Dict[str, Any]]:
        """Load FAQ data for RAG system."""
        query = (
            "SELECT id, question, answer, status, category, tags FROM faqs ORDER BY id"
        )
        params = ()
        rows = self.db.execute_query(query, params)

        faq_data = []
        for row in rows:
            faq_data.append(
                {
                    "id": row[0],
                    "question": row[1],
                    "answer": row[2],
                    "status": row[3],
                    "category": row[4],
                    "tags": self._parse_tags(row[5]),
                }
            )

        return faq_data

    # Validation Methods (Business Logic)

    def _validate_faq_input(self, question: str, answer: str):
        """Validate FAQ question and answer."""
        self._validate_question(question)
        self._validate_answer(answer)

    def _validate_question(self, question: str):
        """Validate FAQ question."""
        if not question or not question.strip():
            raise ValidationError("Question cannot be empty")

        if len(question) > settings.max_question_length:
            raise ValidationError(
                f"Question cannot exceed {settings.max_question_length} characters"
            )

    def _validate_answer(self, answer: str):
        """Validate FAQ answer."""
        if not answer or not answer.strip():
            raise ValidationError("Answer cannot be empty")

        if len(answer) > settings.max_answer_length:
            raise ValidationError(
                f"Answer cannot exceed {settings.max_answer_length} characters"
            )

    def _validate_status(self, status: str):
        """Validate FAQ status."""
        valid_statuses = ["public", "private", "pending"]
        if status not in valid_statuses:
            raise ValidationError(f"Status must be one of: {', '.join(valid_statuses)}")

    def _validate_tags(self, tags: List[str]):
        """Validate FAQ tags."""
        if not tags:
            return

        if len(tags) > 10:
            raise ValidationError("Cannot have more than 10 tags")

        for tag in tags:
            if not tag.strip():
                raise ValidationError("Tags cannot be empty")
            if len(tag) > 50:
                raise ValidationError("Individual tags cannot exceed 50 characters")

    # Utility Methods (Data Access Helpers)

    def _parse_tags(self, tags_json: str) -> List[str]:
        """Parse JSON tags string to list."""
        if not tags_json or tags_json == "":
            return []
        try:
            return json.loads(tags_json)
        except (json.JSONDecodeError, TypeError):
            return []

    def _serialize_tags(self, tags: List[str]) -> str:
        """Serialize tags list to JSON string."""
        return json.dumps(tags) if tags else "[]"

    def _build_where_clause(self, filters: Dict[str, Any]) -> tuple[str, tuple]:
        """Build WHERE clause from filters dictionary."""
        conditions = []
        params = []

        for key, value in filters.items():
            if value is not None:
                if key == "tag":
                    # Special handling for tag filtering
                    conditions.append("(tags != '' AND tags != '[]' AND tags LIKE ?)")
                    params.append(f'%"{value}"%')
                else:
                    conditions.append(f"{key} = ?")
                    params.append(value)

        where_clause = " WHERE " + " AND ".join(conditions) if conditions else ""
        return where_clause, tuple(params)

    def _apply_pagination(
        self, query: str, limit: Optional[int] = None, offset: int = 0
    ) -> str:
        """Apply pagination to a query."""
        if limit is not None:
            query += f" LIMIT {limit}"
            if offset > 0:
                query += f" OFFSET {offset}"
        return query

    def _row_to_faq(self, row) -> FAQResponse:
        """Convert database row to FAQResponse object."""
        return FAQResponse(
            id=row[0],
            question=row[1],
            answer=row[2],
            status=row[3],
            category=row[4],
            tags=self._parse_tags(row[5]),
            created_at=row[6],
            updated_at=row[7],
        )
