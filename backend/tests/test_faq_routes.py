"""
Tests for FAQ routes functionality.
"""

import pytest
from fastapi.testclient import TestClient


class TestFAQRoutes:
    """Test the FAQ routes."""

    def test_get_faqs_endpoint_exists(self, test_client):
        """Test that the GET /faqs endpoint exists and returns data."""
        response = test_client.get("/faqs")
        assert response.status_code == 200

        data = response.json()
        # Check that response has the expected structure
        assert "faqs" in data
        assert "total" in data
        assert "limit" in data
        assert "offset" in data
        assert "has_more" in data

        # Check types
        assert isinstance(data["faqs"], list)
        assert isinstance(data["total"], int)
        assert isinstance(data["limit"], int)
        assert isinstance(data["offset"], int)
        assert isinstance(data["has_more"], bool)

    def test_get_faqs_with_parameters(self, test_client):
        """Test GET /faqs with query parameters."""
        response = test_client.get("/faqs?limit=10&offset=5&status=public")
        assert response.status_code == 200

        data = response.json()
        assert data["limit"] == 10
        assert data["offset"] == 5

    def test_get_faqs_invalid_parameters(self, test_client):
        """Test GET /faqs with invalid parameters."""
        # Test invalid limit (too small)
        response = test_client.get("/faqs?limit=0")
        assert response.status_code == 422

        # Test invalid limit (too large)
        response = test_client.get("/faqs?limit=501")
        assert response.status_code == 422

        # Test invalid offset
        response = test_client.get("/faqs?offset=-1")
        assert response.status_code == 422

    def test_create_faq_endpoint_exists(self, test_client):
        """Test that the POST /faqs endpoint exists."""
        # Test with minimal valid data
        faq_data = {"question": "Test question", "answer": "Test answer"}

        response = test_client.post("/faqs", json=faq_data)
        assert response.status_code == 200

        data = response.json()
        assert "success" in data
        assert "message" in data
        assert "faq" in data
        assert "timestamp" in data

    def test_create_faq_invalid_data(self, test_client):
        """Test POST /faqs with invalid data."""
        # Test missing required fields
        response = test_client.post("/faqs", json={})
        assert response.status_code == 422

        # Test invalid status
        response = test_client.post(
            "/faqs",
            json={"question": "Test", "answer": "Test", "status": "invalid_status"},
        )
        assert response.status_code == 422

    def test_create_faq_with_all_fields(self, test_client):
        """Test POST /faqs with all optional fields."""
        faq_data = {
            "question": "Complete test question",
            "answer": "Complete test answer",
            "status": "public",
            "category": "test",
            "tags": ["tag1", "tag2"],
        }

        response = test_client.post("/faqs", json=faq_data)
        assert response.status_code == 200

        data = response.json()
        assert data["success"] is True
        assert "FAQ created successfully" in data["message"]

    def test_update_faq_endpoint_exists(self, test_client):
        """Test that the PUT /faqs/{id} endpoint exists."""
        # First create an FAQ to update
        create_data = {"question": "Original question", "answer": "Original answer"}

        create_response = test_client.post("/faqs", json=create_data)
        assert create_response.status_code == 200

        created_faq = create_response.json()["faq"]
        faq_id = created_faq["id"]

        # Now update it
        update_data = {"question": "Updated question"}

        response = test_client.put(f"/faqs/{faq_id}", json=update_data)
        assert response.status_code == 200

        data = response.json()
        assert "success" in data
        assert "message" in data
        assert "faq" in data
        assert "old_faq" in data

    def test_update_faq_invalid_id(self, test_client):
        """Test PUT /faqs/{id} with invalid ID."""
        response = test_client.put("/faqs/invalid_id", json={"question": "test"})
        assert response.status_code == 422

    def test_update_faq_invalid_data(self, test_client):
        """Test PUT /faqs/{id} with invalid data."""
        # Use a large ID that likely doesn't exist
        response = test_client.put("/faqs/999999", json={"status": "invalid_status"})
        assert response.status_code == 422

    def test_delete_faq_endpoint_exists(self, test_client):
        """Test that the DELETE /faqs/{id} endpoint exists."""
        # First create an FAQ to delete
        create_data = {"question": "FAQ to delete", "answer": "This will be deleted"}

        create_response = test_client.post("/faqs", json=create_data)
        assert create_response.status_code == 200

        created_faq = create_response.json()["faq"]
        faq_id = created_faq["id"]

        # Now delete it
        response = test_client.delete(f"/faqs/{faq_id}")
        assert response.status_code == 200

        data = response.json()
        assert "success" in data
        assert "message" in data
        assert "deleted_faq" in data

    def test_delete_faq_invalid_id(self, test_client):
        """Test DELETE /faqs/{id} with invalid ID."""
        response = test_client.delete("/faqs/invalid_id")
        assert response.status_code == 422

    def test_get_tags_endpoint_exists(self, test_client):
        """Test that the GET /faqs/tags endpoint exists."""
        response = test_client.get("/faqs/tags")
        assert response.status_code == 200

        data = response.json()
        assert "tags" in data or "count" in data or "timestamp" in data

    def test_get_categories_endpoint_exists(self, test_client):
        """Test that the GET /faqs/categories endpoint exists."""
        response = test_client.get("/faqs/categories")
        assert response.status_code == 200

        data = response.json()
        assert "categories" in data or "total_categories" in data or "timestamp" in data

    def test_get_pending_changes_endpoint_exists(self, test_client):
        """Test that the GET /faqs/pending endpoint exists."""
        response = test_client.get("/faqs/pending")
        assert response.status_code == 200

        data = response.json()
        assert "changes" in data
        assert "total_count" in data
        assert "has_pending" in data
        assert isinstance(data["changes"], list)
        assert isinstance(data["total_count"], int)
        assert isinstance(data["has_pending"], bool)

    def test_route_paths_are_correct(self, test_client):
        """Test that all expected routes are available."""
        # Test that routes don't return 404 (method not allowed is fine)
        routes_to_test = [
            ("/faqs", "GET"),
            ("/faqs", "POST"),
            ("/faqs/tags", "GET"),
            ("/faqs/categories", "GET"),
            ("/faqs/pending", "GET"),
        ]

        for path, method in routes_to_test:
            if method == "GET":
                response = test_client.get(path)
            elif method == "POST":
                response = test_client.post(
                    path, json={"question": "test", "answer": "test"}
                )

            # Should not be 404 (not found)
            assert response.status_code != 404

    def test_faq_crud_workflow(self, test_client):
        """Test a complete CRUD workflow."""
        # Create
        create_data = {
            "question": "CRUD Test Question",
            "answer": "CRUD Test Answer",
            "category": "test",
            "tags": ["crud", "test"],
        }

        create_response = test_client.post("/faqs", json=create_data)
        assert create_response.status_code == 200

        created_faq = create_response.json()["faq"]
        faq_id = created_faq["id"]
        assert created_faq["question"] == "CRUD Test Question"

        # Read (verify it exists in list - check all statuses since new FAQs might be pending)
        list_response = test_client.get("/faqs?limit=500")  # Get more FAQs to find ours
        assert list_response.status_code == 200
        faqs = list_response.json()["faqs"]

        # If not found in default list, try with status=pending
        if not any(faq["id"] == faq_id for faq in faqs):
            pending_response = test_client.get("/faqs?status=pending&limit=500")
            if pending_response.status_code == 200:
                pending_faqs = pending_response.json()["faqs"]
                faqs.extend(pending_faqs)

        # Now check if we can find our FAQ
        found_faq = next((faq for faq in faqs if faq["id"] == faq_id), None)
        assert (
            found_faq is not None
        ), f"Created FAQ with ID {faq_id} not found in any status"

        # Update
        update_data = {"question": "Updated CRUD Question", "category": "updated"}

        update_response = test_client.put(f"/faqs/{faq_id}", json=update_data)
        assert update_response.status_code == 200

        updated_faq = update_response.json()["faq"]
        assert updated_faq["question"] == "Updated CRUD Question"

        # Delete
        delete_response = test_client.delete(f"/faqs/{faq_id}")
        assert delete_response.status_code == 200

        deleted_faq = delete_response.json()["deleted_faq"]
        assert deleted_faq["id"] == faq_id

    def test_response_consistency(self, test_client):
        """Test that responses have consistent structure."""
        # Test FAQ list response
        response = test_client.get("/faqs")
        assert response.status_code == 200
        data = response.json()

        # Check that FAQ objects have consistent structure
        if data["faqs"]:
            faq = data["faqs"][0]
            required_fields = ["id", "question", "answer", "status", "category", "tags"]
            for field in required_fields:
                assert field in faq

        # Test create response
        create_data = {"question": "Consistency test", "answer": "Test answer"}
        create_response = test_client.post("/faqs", json=create_data)
        assert create_response.status_code == 200

        create_data = create_response.json()
        assert "success" in create_data
        assert "message" in create_data
        assert "faq" in create_data
        assert "timestamp" in create_data


if __name__ == "__main__":
    pytest.main([__file__])
