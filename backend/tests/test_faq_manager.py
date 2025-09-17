"""
Tests for FAQManager functionality.
"""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from core.faq import FAQManager
from core.database import DatabaseManager
from core.pending_changes import PendingChangesManager, ChangeType
from core.exceptions import ValidationError, NotFoundError, DatabaseError
from models import FAQResponse, FAQCreateRequest, FAQUpdateRequest


class TestFAQManager:
    """Test the FAQManager class."""

    def setup_method(self):
        """Set up test environment for each test."""
        self.mock_db = Mock(spec=DatabaseManager)
        self.faq_manager = FAQManager(self.mock_db)

        # Mock the pending changes manager
        self.faq_manager.pending_changes = Mock(spec=PendingChangesManager)

    def test_initialization(self):
        """Test FAQManager initialization."""
        assert self.faq_manager.db == self.mock_db
        assert isinstance(self.faq_manager.pending_changes, Mock)

    def test_get_faq_by_id_success(self):
        """Test successful FAQ retrieval by ID."""
        # Mock database response
        mock_row = (
            1,
            "Test question",
            "Test answer",
            "public",
            "general",
            "[]",
            "2024-01-01",
            "2024-01-01",
        )
        self.mock_db.execute_one.return_value = mock_row

        result = self.faq_manager.get_faq_by_id(1)

        assert isinstance(result, FAQResponse)
        assert result.id == 1
        assert result.question == "Test question"
        assert result.answer == "Test answer"
        assert result.status == "public"
        assert result.category == "general"
        assert result.tags == []

    def test_get_faq_by_id_not_found(self):
        """Test FAQ retrieval when FAQ doesn't exist."""
        self.mock_db.execute_one.return_value = None

        with pytest.raises(NotFoundError, match="FAQ not found with ID: 1"):
            self.faq_manager.get_faq_by_id(1)

    def test_get_faqs_success(self):
        """Test successful FAQ listing with pagination."""
        # Mock database responses
        mock_rows = [
            (1, "Q1", "A1", "public", "general", "[]", "2024-01-01", "2024-01-01"),
            (2, "Q2", "A2", "private", "tech", '["tag1"]', "2024-01-02", "2024-01-02"),
        ]
        self.mock_db.execute_one.return_value = (10,)  # total count
        self.mock_db.execute_query.return_value = mock_rows

        result = self.faq_manager.get_faqs(limit=2, offset=0)

        assert result["total"] == 10
        assert result["limit"] == 2
        assert result["offset"] == 0
        assert result["has_more"] is True
        assert len(result["faqs"]) == 2
        assert result["faqs"][0].id == 1
        assert result["faqs"][1].id == 2
        assert "timestamp" in result

    def test_get_faqs_with_filters(self):
        """Test FAQ listing with filters."""
        mock_rows = [
            (1, "Q1", "A1", "public", "general", "[]", "2024-01-01", "2024-01-01")
        ]
        self.mock_db.execute_one.return_value = (1,)
        self.mock_db.execute_query.return_value = mock_rows

        result = self.faq_manager.get_faqs(
            status="public", category="general", tag="test"
        )

        assert len(result["faqs"]) == 1
        assert result["total"] == 1

    def test_get_faqs_invalid_limit(self):
        """Test FAQ listing with invalid limit."""
        with pytest.raises(ValidationError, match="Limit must be between 1 and 500"):
            self.faq_manager.get_faqs(limit=0)

        with pytest.raises(ValidationError, match="Limit must be between 1 and 500"):
            self.faq_manager.get_faqs(limit=501)

    def test_get_faqs_invalid_offset(self):
        """Test FAQ listing with invalid offset."""
        with pytest.raises(ValidationError, match="Offset cannot be negative"):
            self.faq_manager.get_faqs(offset=-1)

    def test_create_faq_success(self):
        """Test successful FAQ creation."""
        request = FAQCreateRequest(
            question="Test question",
            answer="Test answer",
            status="public",
            category="general",
            tags=["tag1", "tag2"],
        )

        # Mock database responses
        self.mock_db.execute_insert.return_value = 1
        mock_row = (
            1,
            "Test question",
            "Test answer",
            "pending",
            "general",
            '["tag1", "tag2"]',
            "2024-01-01",
            "2024-01-01",
        )
        self.mock_db.execute_one.return_value = mock_row

        with (
            patch.object(self.faq_manager, "_validate_faq_input"),
            patch.object(self.faq_manager, "_validate_status"),
            patch.object(self.faq_manager, "_validate_tags"),
        ):

            result = self.faq_manager.create_faq(request)

        assert isinstance(result, FAQResponse)
        assert result.id == 1
        assert result.status == "pending"  # Should be set to pending initially

        # Check pending change was added
        self.faq_manager.pending_changes.add_pending_change.assert_called_once_with(
            faq_id=1, change_type=ChangeType.CREATED, original_status="public"
        )

    def test_create_faq_validation_error(self):
        """Test FAQ creation with validation error."""
        request = FAQCreateRequest(question="", answer="Test answer", status="public")

        with patch.object(
            self.faq_manager,
            "_validate_faq_input",
            side_effect=ValidationError("Question cannot be empty"),
        ):
            with pytest.raises(ValidationError, match="Question cannot be empty"):
                self.faq_manager.create_faq(request)

    def test_update_faq_success(self):
        """Test successful FAQ update."""
        request = FAQUpdateRequest(
            question="Updated question", answer="Updated answer", status="private"
        )

        # Mock existing FAQ
        existing_faq = FAQResponse(
            id=1,
            question="Old question",
            answer="Old answer",
            status="public",
            category="general",
            tags=[],
            created_at="2024-01-01",
            updated_at="2024-01-01",
        )

        # Mock updated FAQ
        updated_row = (
            1,
            "Updated question",
            "Updated answer",
            "pending",
            "general",
            "[]",
            "2024-01-01",
            "2024-01-02",
        )

        with (
            patch.object(self.faq_manager, "get_faq_by_id", return_value=existing_faq),
            patch.object(self.faq_manager, "_validate_question"),
            patch.object(self.faq_manager, "_validate_answer"),
            patch.object(self.faq_manager, "_validate_status"),
            patch.object(self.faq_manager, "_update") as mock_update,
        ):

            mock_update.return_value = FAQResponse(
                id=1,
                question="Updated question",
                answer="Updated answer",
                status="pending",
                category="general",
                tags=[],
                created_at="2024-01-01",
                updated_at="2024-01-02",
            )

            updated_faq, old_faq = self.faq_manager.update_faq(1, request)

        assert updated_faq.question == "Updated question"
        assert updated_faq.status == "pending"
        assert old_faq.question == "Old question"

        # Check pending change was added
        self.faq_manager.pending_changes.add_pending_change.assert_called_once_with(
            faq_id=1,
            change_type=ChangeType.UPDATED,
            original_status="private",  # The intended status
        )

    def test_update_faq_not_found(self):
        """Test FAQ update when FAQ doesn't exist."""
        request = FAQUpdateRequest(question="Updated question")

        with patch.object(
            self.faq_manager,
            "get_faq_by_id",
            side_effect=NotFoundError("FAQ not found"),
        ):
            with pytest.raises(NotFoundError):
                self.faq_manager.update_faq(999, request)

    def test_delete_faq_success(self):
        """Test successful FAQ deletion."""
        existing_faq = FAQResponse(
            id=1,
            question="Test question",
            answer="Test answer",
            status="public",
            category="general",
            tags=[],
            created_at="2024-01-01",
            updated_at="2024-01-01",
        )

        with (
            patch.object(self.faq_manager, "get_faq_by_id", return_value=existing_faq),
            patch.object(self.faq_manager, "_delete", return_value=existing_faq),
        ):

            result = self.faq_manager.delete_faq(1)

        assert result == existing_faq

        # Check pending change was added
        self.faq_manager.pending_changes.add_pending_change.assert_called_once_with(
            faq_id=1, change_type=ChangeType.DELETED, original_status="public"
        )

    def test_delete_faq_not_found(self):
        """Test FAQ deletion when FAQ doesn't exist."""
        with patch.object(
            self.faq_manager,
            "get_faq_by_id",
            side_effect=NotFoundError("FAQ not found"),
        ):
            with pytest.raises(NotFoundError):
                self.faq_manager.delete_faq(999)

    def test_search_faqs_success(self):
        """Test successful FAQ search."""
        mock_rows = [
            (
                1,
                "Python question",
                "Python answer",
                "public",
                "tech",
                "[]",
                "2024-01-01",
                "2024-01-01",
                10.0,
            ),
            (
                2,
                "Java question",
                "Java answer",
                "public",
                "tech",
                "[]",
                "2024-01-02",
                "2024-01-02",
                8.0,
            ),
        ]
        self.mock_db.execute_query.return_value = mock_rows

        result = self.faq_manager.search_faqs("Python", limit=10)

        assert len(result) == 2
        assert result[0].id == 1
        assert result[1].id == 2

    def test_search_faqs_empty_query(self):
        """Test FAQ search with empty query."""
        with pytest.raises(ValidationError, match="Search query cannot be empty"):
            self.faq_manager.search_faqs("")

    def test_search_faqs_invalid_limit(self):
        """Test FAQ search with invalid limit."""
        with pytest.raises(
            ValidationError, match="Search limit must be between 1 and 50"
        ):
            self.faq_manager.search_faqs("test", limit=0)

        with pytest.raises(
            ValidationError, match="Search limit must be between 1 and 50"
        ):
            self.faq_manager.search_faqs("test", limit=51)

    def test_get_all_tags(self):
        """Test getting all tags."""
        mock_rows = [('["tag1", "tag2"]',), ('["tag2", "tag3"]',)]
        self.mock_db.execute_query.return_value = mock_rows

        result = self.faq_manager.get_all_tags()

        assert result["count"] == 3
        assert set(result["tags"]) == {"tag1", "tag2", "tag3"}
        assert "timestamp" in result

    def test_get_all_categories(self):
        """Test getting all categories."""
        mock_rows = [("general", 5), ("tech", 3)]
        self.mock_db.execute_query.return_value = mock_rows

        result = self.faq_manager.get_all_categories()

        assert result["total_categories"] == 2
        assert result["categories"] == [
            {"name": "general", "count": 5},
            {"name": "tech", "count": 3},
        ]
        assert "timestamp" in result

    def test_get_statistics(self):
        """Test getting FAQ statistics."""
        # Mock multiple database calls
        self.mock_db.execute_one.side_effect = [
            (100,),  # total_faqs
            (80,),  # public_faqs
            (20,),  # private_faqs
            (5,),  # recent_faqs
            (50.5,),  # avg_question_length
            (150.2,),  # avg_answer_length
            (200,),  # max_question_length
            (500,),  # max_answer_length
            (75,),  # faqs_with_tags
        ]

        result = self.faq_manager.get_statistics()

        assert result["total_faqs"] == 100
        assert result["public_faqs"] == 80
        assert result["private_faqs"] == 20
        assert result["recent_faqs"] == 5
        assert result["avg_question_length"] == 50.5
        assert result["avg_answer_length"] == 150.2
        assert result["max_question_length"] == 200
        assert result["max_answer_length"] == 500
        assert result["faqs_with_tags"] == 75
        assert "timestamp" in result

    def test_load_faqs_for_rag(self):
        """Test loading FAQs for RAG system."""
        mock_rows = [
            (1, "Q1", "A1", "public", "general", '["tag1"]'),
            (2, "Q2", "A2", "private", "tech", "[]"),
        ]
        self.mock_db.execute_query.return_value = mock_rows

        result = self.faq_manager.load_faqs_for_rag()

        assert len(result) == 2
        assert result[0] == {
            "id": 1,
            "question": "Q1",
            "answer": "A1",
            "status": "public",
            "category": "general",
            "tags": ["tag1"],
        }
        assert result[1] == {
            "id": 2,
            "question": "Q2",
            "answer": "A2",
            "status": "private",
            "category": "tech",
            "tags": [],
        }

    def test_get_pending_changes(self):
        """Test getting pending changes."""
        mock_changes = {"changes": [], "total_count": 0}
        self.faq_manager.pending_changes.get_pending_changes.return_value = mock_changes

        result = self.faq_manager.get_pending_changes()

        assert result == mock_changes
        self.faq_manager.pending_changes.get_pending_changes.assert_called_once()

    def test_restore_faq_statuses_after_rebuild(self):
        """Test restoring FAQ statuses after cache rebuild."""
        from core.pending_changes import PendingChange

        # Mock pending changes
        mock_changes = [
            PendingChange(1, ChangeType.CREATED, "public", "2024-01-01"),
            PendingChange(2, ChangeType.UPDATED, "private", "2024-01-02"),
            PendingChange(
                3, ChangeType.DELETED, "public", "2024-01-03"
            ),  # Should be skipped
        ]

        self.faq_manager.pending_changes.get_changes_for_rebuild.return_value = (
            mock_changes
        )
        self.faq_manager.pending_changes.clear_all_pending_changes.return_value = {
            "cleared_count": 3
        }

        with patch.object(
            self.faq_manager, "_update_status_only"
        ) as mock_update_status:
            result = self.faq_manager.restore_faq_statuses_after_rebuild()

        assert result["success"] is True
        assert result["restored_count"] == 2  # Only created and updated, not deleted
        assert result["cleared_count"] == 3
        assert "timestamp" in result

        # Check that status updates were called for non-deleted FAQs
        assert mock_update_status.call_count == 2
        mock_update_status.assert_any_call(1, "public")
        mock_update_status.assert_any_call(2, "private")

    def test_restore_faq_statuses_database_error(self):
        """Test restore FAQ statuses with database error."""
        self.faq_manager.pending_changes.get_changes_for_rebuild.side_effect = (
            Exception("DB Error")
        )

        with pytest.raises(DatabaseError, match="Failed to restore FAQ statuses"):
            self.faq_manager.restore_faq_statuses_after_rebuild()

    def test_update_status_only(self):
        """Test internal _update_status_only method."""
        self.faq_manager._update_status_only(1, "public")

        self.mock_db.execute_query.assert_called_once()
        call_args = self.mock_db.execute_query.call_args
        assert "UPDATE faqs SET status = ?" in call_args[0][0]
        assert call_args[0][1][0] == "public"
        assert call_args[0][1][2] == 1

    def test_validate_faq_input_success(self):
        """Test successful FAQ input validation."""
        with (
            patch.object(self.faq_manager, "_validate_question"),
            patch.object(self.faq_manager, "_validate_answer"),
        ):

            # Should not raise any exception
            self.faq_manager._validate_faq_input("Valid question", "Valid answer")

    def test_validate_question_empty(self):
        """Test question validation with empty question."""
        with pytest.raises(ValidationError, match="Question cannot be empty"):
            self.faq_manager._validate_question("")

    def test_validate_question_too_long(self):
        """Test question validation with too long question."""
        with patch("core.faq.settings") as mock_settings:
            mock_settings.max_question_length = 10

            with pytest.raises(
                ValidationError, match="Question cannot exceed 10 characters"
            ):
                self.faq_manager._validate_question("This is a very long question")

    def test_validate_answer_empty(self):
        """Test answer validation with empty answer."""
        with pytest.raises(ValidationError, match="Answer cannot be empty"):
            self.faq_manager._validate_answer("")

    def test_validate_answer_too_long(self):
        """Test answer validation with too long answer."""
        with patch("core.faq.settings") as mock_settings:
            mock_settings.max_answer_length = 10

            with pytest.raises(
                ValidationError, match="Answer cannot exceed 10 characters"
            ):
                self.faq_manager._validate_answer("This is a very long answer")

    def test_validate_status_valid(self):
        """Test status validation with valid statuses."""
        # Should not raise exceptions
        self.faq_manager._validate_status("public")
        self.faq_manager._validate_status("private")
        self.faq_manager._validate_status("pending")

    def test_validate_status_invalid(self):
        """Test status validation with invalid status."""
        with pytest.raises(ValidationError, match="Status must be one of"):
            self.faq_manager._validate_status("invalid")

    def test_validate_tags_valid(self):
        """Test tags validation with valid tags."""
        # Should not raise exceptions
        self.faq_manager._validate_tags(["tag1", "tag2"])
        self.faq_manager._validate_tags([])
        self.faq_manager._validate_tags(None)

    def test_validate_tags_too_many(self):
        """Test tags validation with too many tags."""
        tags = [f"tag{i}" for i in range(11)]  # 11 tags

        with pytest.raises(ValidationError, match="Cannot have more than 10 tags"):
            self.faq_manager._validate_tags(tags)

    def test_validate_tags_empty_tag(self):
        """Test tags validation with empty tag."""
        with pytest.raises(ValidationError, match="Tags cannot be empty"):
            self.faq_manager._validate_tags(["", "valid_tag"])

    def test_validate_tags_too_long(self):
        """Test tags validation with too long tag."""
        long_tag = "a" * 51  # 51 characters

        with pytest.raises(
            ValidationError, match="Individual tags cannot exceed 50 characters"
        ):
            self.faq_manager._validate_tags([long_tag])

    def test_parse_tags_valid_json(self):
        """Test parsing valid JSON tags."""
        result = self.faq_manager._parse_tags('["tag1", "tag2"]')
        assert result == ["tag1", "tag2"]

    def test_parse_tags_empty_string(self):
        """Test parsing empty tags string."""
        result = self.faq_manager._parse_tags("")
        assert result == []

    def test_parse_tags_invalid_json(self):
        """Test parsing invalid JSON tags."""
        result = self.faq_manager._parse_tags("invalid json")
        assert result == []

    def test_serialize_tags_valid(self):
        """Test serializing valid tags."""
        result = self.faq_manager._serialize_tags(["tag1", "tag2"])
        assert result == '["tag1", "tag2"]'

    def test_serialize_tags_empty(self):
        """Test serializing empty tags."""
        result = self.faq_manager._serialize_tags([])
        assert result == "[]"

        result = self.faq_manager._serialize_tags(None)
        assert result == "[]"

    def test_build_where_clause_no_filters(self):
        """Test building WHERE clause with no filters."""
        where_clause, params = self.faq_manager._build_where_clause({})
        assert where_clause == ""
        assert params == ()

    def test_build_where_clause_with_filters(self):
        """Test building WHERE clause with filters."""
        filters = {"status": "public", "category": "general"}
        where_clause, params = self.faq_manager._build_where_clause(filters)

        assert " WHERE " in where_clause
        assert "status = ?" in where_clause
        assert "category = ?" in where_clause
        assert params == ("public", "general")

    def test_build_where_clause_with_tag_filter(self):
        """Test building WHERE clause with tag filter."""
        filters = {"tag": "python"}
        where_clause, params = self.faq_manager._build_where_clause(filters)

        assert "tags LIKE ?" in where_clause
        assert params == ('%"python"%',)

    def test_apply_pagination_with_limit(self):
        """Test applying pagination with limit."""
        query = "SELECT * FROM faqs"
        result = self.faq_manager._apply_pagination(query, limit=10)
        assert result == "SELECT * FROM faqs LIMIT 10"

    def test_apply_pagination_with_limit_and_offset(self):
        """Test applying pagination with limit and offset."""
        query = "SELECT * FROM faqs"
        result = self.faq_manager._apply_pagination(query, limit=10, offset=20)
        assert result == "SELECT * FROM faqs LIMIT 10 OFFSET 20"

    def test_apply_pagination_no_limit(self):
        """Test applying pagination without limit."""
        query = "SELECT * FROM faqs"
        result = self.faq_manager._apply_pagination(query)
        assert result == "SELECT * FROM faqs"

    def test_row_to_faq(self):
        """Test converting database row to FAQResponse."""
        row = (
            1,
            "Question",
            "Answer",
            "public",
            "general",
            '["tag1"]',
            "2024-01-01",
            "2024-01-02",
        )

        result = self.faq_manager._row_to_faq(row)

        assert isinstance(result, FAQResponse)
        assert result.id == 1
        assert result.question == "Question"
        assert result.answer == "Answer"
        assert result.status == "public"
        assert result.category == "general"
        assert result.tags == ["tag1"]
        assert result.created_at == "2024-01-01"
        assert result.updated_at == "2024-01-02"


if __name__ == "__main__":
    pytest.main([__file__])
