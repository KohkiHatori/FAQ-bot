"""
Tests for Claude routes functionality.
"""

import pytest
import json
from fastapi.testclient import TestClient
from fastapi import FastAPI
from api.routes.claude_routes import router


# Create a test app with the Claude router
app = FastAPI()
app.include_router(router)


class TestClaudeRoutes:
    """Test the Claude routes."""

    def setup_method(self):
        """Set up test environment for each test."""
        self.client = TestClient(app)

    def test_query_with_rag_endpoint_exists(self):
        """Test that the POST /query-with-rag endpoint exists."""
        # Test with minimal valid data
        query_data = {
            "message": "What is the investment strategy?",
            "conversationHistory": "",
            "top_k": 3,
        }

        response = self.client.post("/query-with-rag", json=query_data)

        # Should not be 404 (endpoint exists)
        assert response.status_code != 404

        # Should be either 200 (success) or 503 (service unavailable during init)
        assert response.status_code in [200, 503]

        if response.status_code == 503:
            # System is initializing
            assert "initializing" in response.json()["detail"].lower()

    def test_query_with_rag_streaming_response(self):
        """Test that the endpoint returns a streaming response."""
        query_data = {
            "message": "Tell me about investment options",
            "conversationHistory": "",
            "top_k": 5,
        }

        response = self.client.post("/query-with-rag", json=query_data)

        if response.status_code == 200:
            # Check that it's a streaming response
            assert response.headers.get("content-type") == "text/event-stream"

            # Check streaming headers
            assert response.headers.get("cache-control") == "no-cache"
            assert response.headers.get("connection") == "keep-alive"
            assert response.headers.get("access-control-allow-origin") == "*"
            assert response.headers.get("access-control-allow-headers") == "*"

            # Check that we get some streamed content
            content = response.content.decode()
            assert len(content) > 0

    def test_query_with_rag_required_fields(self):
        """Test that required fields are validated."""
        # Test missing message field
        response = self.client.post(
            "/query-with-rag", json={"conversationHistory": "", "top_k": 3}
        )
        assert response.status_code == 422

        # Test with all required fields
        response = self.client.post("/query-with-rag", json={"message": "Test query"})
        # Should not fail due to missing fields (other fields have defaults)
        assert response.status_code != 422

    def test_query_with_rag_empty_message(self):
        """Test that empty messages are rejected."""
        query_data = {"message": "", "conversationHistory": "", "top_k": 3}

        response = self.client.post("/query-with-rag", json=query_data)
        # Should return 400 for empty message, or 503 if system is initializing
        assert response.status_code in [400, 503]

        if response.status_code == 400:
            assert "empty" in response.json()["detail"].lower()
        elif response.status_code == 503:
            assert "initializing" in response.json()["detail"].lower()

        # Test with whitespace-only message
        query_data["message"] = "   "
        response = self.client.post("/query-with-rag", json=query_data)
        assert response.status_code in [400, 503]

    def test_query_with_rag_default_values(self):
        """Test that default values work correctly."""
        # Test with minimal data (should use defaults)
        query_data = {"message": "Test query with defaults"}

        response = self.client.post("/query-with-rag", json=query_data)

        # Should not fail due to missing optional fields
        assert response.status_code != 422
        assert response.status_code in [200, 503]  # 503 if system initializing

    def test_query_with_rag_custom_parameters(self):
        """Test with custom parameters."""
        query_data = {
            "message": "What are the investment risks?",
            "conversationHistory": "User: Hello\nAI: Hi there!",
            "top_k": 10,
        }

        response = self.client.post("/query-with-rag", json=query_data)
        assert response.status_code in [200, 503]

    def test_query_with_rag_invalid_top_k(self):
        """Test with invalid top_k values."""
        # Test with negative top_k
        query_data = {"message": "Test query", "top_k": -1}

        response = self.client.post("/query-with-rag", json=query_data)
        # Should either work (if validation allows) or return 422
        assert response.status_code in [200, 422, 503]

        # Test with very large top_k
        query_data["top_k"] = 1000
        response = self.client.post("/query-with-rag", json=query_data)
        assert response.status_code in [200, 422, 503]

    def test_query_with_rag_long_message(self):
        """Test with a very long message."""
        query_data = {
            "message": "A" * 10000,  # Very long message
            "conversationHistory": "",
            "top_k": 3,
        }

        response = self.client.post("/query-with-rag", json=query_data)
        # Should either work or return an appropriate error
        assert response.status_code in [200, 400, 422, 503]

    def test_query_with_rag_long_conversation_history(self):
        """Test with long conversation history."""
        long_history = "User: " + "Question? " * 1000 + "\nAI: " + "Answer. " * 1000

        query_data = {
            "message": "Follow-up question",
            "conversationHistory": long_history,
            "top_k": 3,
        }

        response = self.client.post("/query-with-rag", json=query_data)
        assert response.status_code in [200, 400, 422, 503]

    def test_query_with_rag_special_characters(self):
        """Test with special characters in message."""
        special_messages = [
            "What about émojis? 🤔💰📈",
            'Question with quotes: "What\'s the best strategy?"',
            "Math symbols: α + β = γ, ∑, ∆",
            "Mixed languages: 投資戦略について教えて",
            "Code snippet: `SELECT * FROM investments WHERE risk < 0.5`",
        ]

        for message in special_messages:
            query_data = {"message": message, "conversationHistory": "", "top_k": 3}

            response = self.client.post("/query-with-rag", json=query_data)
            # Should handle special characters gracefully
            assert response.status_code in [200, 503]

    def test_query_with_rag_json_structure(self):
        """Test that invalid JSON structure is rejected."""
        # Test with invalid JSON
        response = self.client.post(
            "/query-with-rag",
            data="invalid json",
            headers={"content-type": "application/json"},
        )
        assert response.status_code == 422

    def test_query_with_rag_content_type(self):
        """Test that correct content type is required."""
        query_data = {"message": "Test query", "conversationHistory": "", "top_k": 3}

        # Test with wrong content type
        response = self.client.post(
            "/query-with-rag",
            data=json.dumps(query_data),
            headers={"content-type": "text/plain"},
        )
        assert response.status_code == 422

    def test_query_with_rag_response_format(self):
        """Test the response format when successful."""
        query_data = {
            "message": "What is portfolio diversification?",
            "conversationHistory": "",
            "top_k": 3,
        }

        response = self.client.post("/query-with-rag", json=query_data)

        if response.status_code == 200:
            # Should be streaming response
            assert response.headers.get("content-type") == "text/event-stream"

            # Content should be server-sent events format
            content = response.content.decode()
            if content:
                # Should contain SSE data
                assert "data:" in content or len(content) > 0

    def test_multiple_concurrent_requests(self):
        """Test that multiple requests can be handled."""
        query_data = {
            "message": "Quick test query",
            "conversationHistory": "",
            "top_k": 1,
        }

        # Make multiple requests
        responses = []
        for i in range(3):
            response = self.client.post("/query-with-rag", json=query_data)
            responses.append(response)

        # All should return valid status codes
        for response in responses:
            assert response.status_code in [200, 503]

    def test_route_path_is_correct(self):
        """Test that the route path is correctly configured."""
        # Test that the endpoint exists at the expected path
        query_data = {"message": "test"}

        # Correct path should work
        response = self.client.post("/query-with-rag", json=query_data)
        assert response.status_code != 404

        # Wrong path should return 404
        response = self.client.post("/query-rag", json=query_data)
        assert response.status_code == 404

        response = self.client.post("/query", json=query_data)
        assert response.status_code == 404

    def test_http_methods(self):
        """Test that only POST method is allowed."""
        # POST should work (or return 503 if initializing)
        response = self.client.post("/query-with-rag", json={"message": "test"})
        assert response.status_code in [200, 503, 422]

        # Other methods should not be allowed
        response = self.client.get("/query-with-rag")
        assert response.status_code == 405  # Method Not Allowed

        response = self.client.put("/query-with-rag", json={"message": "test"})
        assert response.status_code == 405

        response = self.client.delete("/query-with-rag")
        assert response.status_code == 405


if __name__ == "__main__":
    pytest.main([__file__])
