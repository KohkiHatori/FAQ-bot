"""
Tests for the main FastAPI application.
"""

import pytest
from fastapi.testclient import TestClient


class TestApp:
    """Test the main FastAPI application."""

    def test_app_creation(self, test_app):
        """Test that the app is created successfully."""
        assert test_app is not None
        assert test_app.title == "FAQ Bot API"

    def test_app_docs_endpoints(self, test_client):
        """Test that documentation endpoints are available."""
        # Test OpenAPI docs
        response = test_client.get("/docs")
        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")

        # Test ReDoc
        response = test_client.get("/redoc")
        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")

        # Test OpenAPI JSON
        response = test_client.get("/openapi.json")
        assert response.status_code == 200
        assert "application/json" in response.headers.get("content-type", "")

        openapi_data = response.json()
        assert openapi_data["info"]["title"] == "FAQ Bot API"
        assert openapi_data["info"]["version"] == "2.0.0"

    def test_cors_middleware(self, test_client):
        """Test that CORS middleware is properly configured."""
        # Test preflight request
        response = test_client.options(
            "/",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "content-type",
            },
        )

        # Should allow CORS
        assert response.status_code in [200, 204]

        # Test actual request with origin
        response = test_client.get("/", headers={"Origin": "http://localhost:3000"})
        assert response.status_code == 200

        # Should have CORS headers
        cors_headers = response.headers
        assert "access-control-allow-origin" in cors_headers

    def test_health_router_included(self, test_client):
        """Test that health router is included."""
        response = test_client.get("/")
        assert response.status_code == 200

        data = response.json()
        assert data["message"] == "RAG FAQ Bot API"
        assert data["version"] == "2.0.0"

    def test_faq_router_included(self, test_client):
        """Test that FAQ router is included."""
        response = test_client.get("/faqs")
        assert response.status_code == 200

        data = response.json()
        assert "faqs" in data

    def test_cache_router_included(self, test_client):
        """Test that cache router is included."""
        response = test_client.get("/cache")
        assert response.status_code == 200

        data = response.json()
        assert "cached" in data

    def test_claude_router_included(self, test_client):
        """Test that Claude router is included."""
        response = test_client.post("/query-with-rag", json={"message": "test"})
        assert response.status_code in [200, 400, 503]

    def test_error_handling(self, test_client):
        """Test that error handlers are registered."""
        # Test 404 error
        response = test_client.get("/nonexistent-endpoint")
        assert response.status_code == 404

        # Should return JSON error response
        data = response.json()
        assert "detail" in data

    def test_app_metadata(self, test_client):
        """Test application metadata through OpenAPI."""
        response = test_client.get("/openapi.json")
        assert response.status_code == 200

        openapi_data = response.json()
        info = openapi_data["info"]

        assert info["title"] == "FAQ Bot API"
        assert (
            info["description"]
            == "A smart FAQ bot with RAG-powered search and Claude AI integration"
        )
        assert info["version"] == "2.0.0"

    def test_api_endpoints_structure(self, test_client):
        """Test that all expected API endpoints are available."""
        response = test_client.get("/openapi.json")
        assert response.status_code == 200

        openapi_data = response.json()
        paths = openapi_data["paths"]

        # Health endpoints
        assert "/" in paths
        assert "/health" in paths

        # FAQ endpoints
        assert "/faqs" in paths

        # Cache endpoints
        assert "/cache" in paths
        assert "/cache/rebuild" in paths

        # Claude endpoint
        assert "/query-with-rag" in paths

    def test_app_tags(self, test_client):
        """Test that API endpoints are properly tagged."""
        response = test_client.get("/openapi.json")
        assert response.status_code == 200

        openapi_data = response.json()

        # Check that tags are defined
        if "tags" in openapi_data:
            tag_names = [tag["name"] for tag in openapi_data["tags"]]
            expected_tags = ["Health", "FAQ Management", "Cache", "Claude AI"]

            # At least some of these tags should be present
            assert any(tag in tag_names for tag in expected_tags)

    def test_startup_behavior(self, test_client):
        """Test that the app starts up correctly."""
        # The app should be ready to serve requests
        response = test_client.get("/health")
        assert response.status_code == 200

        # Should have proper structure indicating startup completed
        data = response.json()
        assert "components" in data
        assert isinstance(data["components"], dict)

    def test_multiple_concurrent_requests(self, test_client):
        """Test that the app can handle multiple concurrent requests."""
        import threading

        results = []

        def make_request():
            response = test_client.get("/health")
            results.append(response.status_code)

        # Create multiple threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=make_request)
            threads.append(thread)

        # Start all threads
        for thread in threads:
            thread.start()

        # Wait for completion
        for thread in threads:
            thread.join()

        # All should succeed
        assert len(results) == 5
        for status_code in results:
            assert status_code == 200

    def test_request_response_cycle(self, test_client):
        """Test complete request-response cycle."""
        # Make a request that exercises the full stack
        response = test_client.get("/")

        assert response.status_code == 200
        assert response.headers.get("content-type") == "application/json"

        data = response.json()
        assert isinstance(data, dict)
        assert "message" in data
        assert "status" in data
        assert "version" in data


if __name__ == "__main__":
    pytest.main([__file__])
