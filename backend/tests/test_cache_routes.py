"""
Tests for cache routes functionality with mocked dependencies for fast execution.
"""

import pytest
from unittest.mock import Mock
from fastapi.testclient import TestClient
from fastapi import FastAPI
from api.routes.cache_routes import router
from api.dependencies import get_vector_store, get_faq_manager


# Create a test app with the cache router
app = FastAPI()
app.include_router(router)


class TestCacheRoutes:
    """Test the cache routes with mocked dependencies."""

    def setup_method(self):
        """Set up test environment for each test."""
        # Create mock objects
        self.mock_vector_store = Mock()
        self.mock_faq_manager = Mock()

        # Configure mock vector store default behavior to match actual VectorStore.get_cache_info()
        self.mock_vector_store.get_cache_info.return_value = {
            "cached": True,
            "model_name": "all-MiniLM-L6-v2",
            "document_count": 134,
            "embedding_dimension": 384,
            "distance_metric": "cosine",
            "created_at": "2024-01-01T00:00:00",
            "cache_dir": "/path/to/cache",
            "timestamp": "2024-01-01T00:00:00",
        }

        self.mock_vector_store.rebuild_cache.return_value = {
            "success": True,
            "message": "Cache rebuilt successfully with 134 documents",
        }

        # Override dependencies
        app.dependency_overrides[get_vector_store] = lambda: self.mock_vector_store
        app.dependency_overrides[get_faq_manager] = lambda: self.mock_faq_manager

        # Create test client after overriding dependencies
        self.client = TestClient(app)

    def teardown_method(self):
        """Clean up after each test."""
        # Clear dependency overrides
        app.dependency_overrides.clear()

    def test_get_cache_info_endpoint_exists(self):
        """Test that the GET /cache endpoint exists."""
        response = self.client.get("/cache")
        assert response.status_code == 200

    def test_rebuild_cache_endpoint_exists(self):
        """Test that the POST /cache/rebuild endpoint exists."""
        response = self.client.post("/cache/rebuild")
        assert response.status_code == 200

    def test_cache_info_response_structure(self):
        """Test that cache info returns the expected structure."""
        response = self.client.get("/cache")
        assert response.status_code == 200

        data = response.json()
        # Check fields that exist in CacheInfoResponse model
        assert "cached" in data
        assert data["cached"] is True
        assert "metadata" in data
        assert isinstance(data["metadata"], dict)

        # Check that metadata contains the mapped fields from VectorStore
        metadata = data["metadata"]
        assert "model_name" in metadata
        assert "document_count" in metadata
        assert "embedding_dimension" in metadata
        assert "distance_metric" in metadata
        assert "created_at" in metadata
        assert "timestamp" in metadata

        # Check other CacheInfoResponse fields
        assert "cache_dir" in data
        assert "file_sizes" in data
        assert "error" in data
        assert data["error"] is None  # Should be None when cached=True

    def test_rebuild_cache_response_structure(self):
        """Test that cache rebuild returns the expected structure."""
        response = self.client.post("/cache/rebuild")
        assert response.status_code == 200

        data = response.json()
        assert "success" in data
        assert "message" in data
        assert "timestamp" in data
        assert data["success"] is True

    def test_http_methods(self):
        """Test HTTP methods."""
        # GET /cache should work
        response = self.client.get("/cache")
        assert response.status_code == 200

        # POST /cache should not be allowed
        response = self.client.post("/cache")
        assert response.status_code == 405

        # POST /cache/rebuild should work
        response = self.client.post("/cache/rebuild")
        assert response.status_code == 200

        # GET /cache/rebuild should not be allowed
        response = self.client.get("/cache/rebuild")
        assert response.status_code == 405

    def test_cache_workflow(self):
        """Test a complete cache workflow: info -> rebuild -> info."""
        # Get initial cache info
        info_response = self.client.get("/cache")
        assert info_response.status_code == 200

        initial_data = info_response.json()
        assert "cached" in initial_data

        # Rebuild cache
        rebuild_response = self.client.post("/cache/rebuild")
        assert rebuild_response.status_code == 200

        rebuild_data = rebuild_response.json()
        assert rebuild_data["success"] is True

        # Get cache info after rebuild
        final_info_response = self.client.get("/cache")
        assert final_info_response.status_code == 200

        final_data = final_info_response.json()
        assert "cached" in final_data

        # Verify mock calls
        assert self.mock_vector_store.get_cache_info.call_count == 2
        self.mock_vector_store.rebuild_cache.assert_called_once()

    def test_multiple_cache_rebuild_requests(self):
        """Test that multiple cache rebuild requests work correctly."""
        # Make multiple rebuild requests
        responses = []
        for i in range(3):
            response = self.client.post("/cache/rebuild")
            responses.append(response)

        # All should succeed
        for response in responses:
            assert response.status_code == 200
            data = response.json()
            assert "success" in data
            assert "message" in data

        # Verify mock was called 3 times
        assert self.mock_vector_store.rebuild_cache.call_count == 3

    def test_route_paths(self):
        """Test that routes are correctly configured."""
        # Correct paths should work
        response = self.client.get("/cache")
        assert response.status_code == 200

        response = self.client.post("/cache/rebuild")
        assert response.status_code == 200

        # Incorrect paths should return 404
        response = self.client.get("/caches")
        assert response.status_code == 404

        response = self.client.post("/cache/clear")
        assert response.status_code == 404

    def test_dependency_injection(self):
        """Test that dependencies are properly injected."""
        # Test cache info endpoint
        response = self.client.get("/cache")
        assert response.status_code == 200

        # Verify vector store dependency was called
        self.mock_vector_store.get_cache_info.assert_called()

        # Test cache rebuild endpoint
        response = self.client.post("/cache/rebuild")
        assert response.status_code == 200

        # Verify both dependencies were called
        self.mock_vector_store.rebuild_cache.assert_called_with(self.mock_faq_manager)

    def test_cache_failure_scenario(self):
        """Test cache operations when they fail."""
        # Configure mock for failure
        self.mock_vector_store.rebuild_cache.return_value = {
            "success": False,
            "message": "Failed to rebuild cache: Database error",
        }

        response = self.client.post("/cache/rebuild")
        assert response.status_code == 200

        data = response.json()
        assert data["success"] is False
        assert "failed" in data["message"].lower()

    def test_cache_not_ready_scenario(self):
        """Test cache info when cache is not ready."""
        # Configure mock for uncached state
        self.mock_vector_store.get_cache_info.return_value = {
            "cached": False,
            "message": "Cache not found",
        }

        response = self.client.get("/cache")
        assert response.status_code == 200

        data = response.json()
        assert data["cached"] is False
        # Now the route properly maps 'message' to 'error' field
        assert data["error"] == "Cache not found"


if __name__ == "__main__":
    pytest.main([__file__])
