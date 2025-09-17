"""
Tests for health routes functionality.
"""

import pytest
import json
from datetime import datetime
from fastapi.testclient import TestClient
from fastapi import FastAPI
from api.routes.health_routes import router


# Create a test app with the health router
app = FastAPI()
app.include_router(router)


class TestHealthRoutes:
    """Test the health routes."""

    def setup_method(self):
        """Set up test environment for each test."""
        self.client = TestClient(app)

    def test_root_endpoint_exists(self):
        """Test that the GET / endpoint exists."""
        response = self.client.get("/")

        # Should not be 404 (endpoint exists)
        assert response.status_code != 404

        # Should return 200 for root endpoint
        assert response.status_code == 200

    def test_root_response_structure(self):
        """Test that root endpoint returns the expected structure."""
        response = self.client.get("/")
        assert response.status_code == 200

        data = response.json()

        # Check required fields
        assert "message" in data
        assert "status" in data
        assert "version" in data

        # Check values
        assert data["message"] == "RAG FAQ Bot API"
        assert data["status"] in ["ready", "initializing"]
        assert data["version"] == "2.0.0"

    def test_health_check_endpoint_exists(self):
        """Test that the GET /health endpoint exists."""
        response = self.client.get("/health")

        # Should not be 404 (endpoint exists)
        assert response.status_code != 404

        # Should return 200 for health check
        assert response.status_code == 200

    def test_health_check_response_structure(self):
        """Test that health check returns the expected structure."""
        response = self.client.get("/health")
        assert response.status_code == 200

        data = response.json()

        # Check required fields
        assert "status" in data
        assert "timestamp" in data
        assert "components" in data

        # Check status values
        assert data["status"] in ["healthy", "initializing"]

        # Check components structure
        components = data["components"]
        assert isinstance(components, dict)
        assert "rag_manager" in components
        assert "claude_handler" in components
        assert "system_ready" in components

    def test_http_methods(self):
        """Test that only GET method is allowed."""
        # GET should work for both endpoints
        response = self.client.get("/")
        assert response.status_code == 200

        response = self.client.get("/health")
        assert response.status_code == 200

        # Other methods should not be allowed
        response = self.client.post("/")
        assert response.status_code == 405

        response = self.client.post("/health")
        assert response.status_code == 405


if __name__ == "__main__":
    pytest.main([__file__])
