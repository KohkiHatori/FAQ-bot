"""
Tests for Claude AI client integration.
"""

import pytest
import asyncio
import json
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from core.claude_client import ClaudeClient, Message
from core.exceptions import ExternalServiceError
from core.config import Settings


class TestMessage:
    """Test the Message class."""

    def test_message_creation(self):
        """Test creating Message object."""
        timestamp = datetime.now()
        sender = {"id": "user1", "name": "Test User"}

        message = Message(
            id="msg1",
            content="Hello world",
            sender=sender,
            timestamp=timestamp,
            isCurrentUser=True,
        )

        assert message.id == "msg1"
        assert message.content == "Hello world"
        assert message.sender == sender
        assert message.timestamp == timestamp
        assert message.isCurrentUser is True

    def test_message_creation_defaults(self):
        """Test Message creation with default values."""
        timestamp = datetime.now()
        sender = {"id": "user1"}

        message = Message(
            id="msg1", content="Hello", sender=sender, timestamp=timestamp
        )

        assert message.isCurrentUser is False


class TestClaudeClient:
    """Test the ClaudeClient class."""

    def setup_method(self):
        """Set up test environment for each test."""
        self.mock_settings = Mock(spec=Settings)
        self.mock_settings.aws_access_key_id = "test_access_key"
        self.mock_settings.aws_secret_access_key = "test_secret_key"
        self.mock_settings.aws_region = "us-east-1"
        self.mock_settings.claude_model = "claude-3-sonnet-20240229"

    @patch("core.claude_client.settings")
    @patch("core.claude_client.boto3.client")
    def test_initialization_success(self, mock_boto_client, mock_settings):
        """Test successful ClaudeClient initialization."""
        mock_settings.aws_access_key_id = "test_key"
        mock_settings.aws_secret_access_key = "test_secret"
        mock_settings.aws_region = "us-east-1"
        mock_settings.claude_model = "claude-3-sonnet-20240229"

        mock_bedrock_client = Mock()
        mock_boto_client.return_value = mock_bedrock_client

        client = ClaudeClient()

        assert client.region == "us-east-1"
        assert client.model_id == "claude-3-sonnet-20240229"
        assert client.bedrock_client == mock_bedrock_client

    @patch("core.claude_client.settings")
    @patch("core.claude_client.boto3.client")
    def test_initialization_boto3_error(self, mock_boto_client, mock_settings):
        """Test ClaudeClient initialization with boto3 error."""
        mock_settings.aws_access_key_id = "test_key"
        mock_settings.aws_secret_access_key = "test_secret"
        mock_settings.aws_region = "us-east-1"
        mock_settings.claude_model = "claude-3-sonnet-20240229"

        mock_boto_client.side_effect = Exception("AWS configuration error")

        client = ClaudeClient()
        assert client.bedrock_client is None

    def test_initialize_success(self):
        """Test successful client initialization."""
        with patch("core.claude_client.settings", self.mock_settings):
            with patch("core.claude_client.boto3.client") as mock_boto:
                mock_bedrock_client = Mock()
                mock_boto.return_value = mock_bedrock_client

                client = ClaudeClient()
                result = client.initialize()

                assert result is True
                assert client._initialized is True

    def test_initialize_credential_validation_failure(self):
        """Test initialization with credential validation failure."""
        settings_no_creds = Mock(spec=Settings)
        settings_no_creds.aws_access_key_id = None
        settings_no_creds.aws_secret_access_key = "test_secret"
        settings_no_creds.aws_region = "us-east-1"
        settings_no_creds.claude_model = "claude-3-sonnet-20240229"

        with patch("core.claude_client.settings", settings_no_creds):
            with patch("core.claude_client.boto3.client"):
                client = ClaudeClient()
                result = client.initialize()

                assert result is False
                assert client._initialized is False

    def test_is_ready_true(self):
        """Test is_ready returns True when initialized."""
        with patch("core.claude_client.settings", self.mock_settings):
            with patch("core.claude_client.boto3.client") as mock_boto:
                mock_boto.return_value = Mock()

                client = ClaudeClient()
                client._initialized = True

                assert client.is_ready() is True

    def test_is_ready_false(self):
        """Test is_ready returns False when not initialized."""
        with patch("core.claude_client.settings", self.mock_settings):
            with patch("core.claude_client.boto3.client") as mock_boto:
                mock_boto.return_value = Mock()

                client = ClaudeClient()
                client._initialized = False

                assert client.is_ready() is False

    def test_validate_credentials_success(self):
        """Test successful credential validation."""
        with patch("core.claude_client.settings", self.mock_settings):
            with patch("core.claude_client.boto3.client") as mock_boto:
                mock_boto.return_value = Mock()

                client = ClaudeClient()
                is_valid, error_msg = client.validate_credentials()

                assert is_valid is True
                assert error_msg == ""

    def test_validate_credentials_missing_access_key(self):
        """Test credential validation with missing access key."""
        settings_no_access = Mock(spec=Settings)
        settings_no_access.aws_access_key_id = None
        settings_no_access.aws_secret_access_key = "test_secret"
        settings_no_access.aws_region = "us-east-1"
        settings_no_access.claude_model = "claude-3-sonnet-20240229"

        with patch("core.claude_client.settings", settings_no_access):
            with patch("core.claude_client.boto3.client") as mock_boto:
                mock_boto.return_value = Mock()

                client = ClaudeClient()
                is_valid, error_msg = client.validate_credentials()

                assert is_valid is False
                assert "AWS credentials not configured" in error_msg

    def test_validate_credentials_no_bedrock_client(self):
        """Test credential validation with no bedrock client."""
        with patch("core.claude_client.settings", self.mock_settings):
            with patch("core.claude_client.boto3.client") as mock_boto:
                mock_boto.return_value = None

                client = ClaudeClient()
                client.bedrock_client = None
                is_valid, error_msg = client.validate_credentials()

                assert is_valid is False
                assert "Failed to initialize AWS Bedrock client" in error_msg

    def test_build_conversation_context(self):
        """Test building conversation context from message history."""
        with patch("core.claude_client.settings", self.mock_settings):
            with patch("core.claude_client.boto3.client") as mock_boto:
                mock_boto.return_value = Mock()

                client = ClaudeClient()

                messages = [
                    Message("1", "Hello", {"id": "user1"}, datetime.now()),
                    Message("2", "How are you?", {"id": "susten-ai"}, datetime.now()),
                    Message("3", "What is Python?", {"id": "user1"}, datetime.now()),
                ]

                context = client.build_conversation_context(messages)

                assert "User: Hello" in context
                assert "User: What is Python?" in context
                assert "How are you?" not in context  # AI messages filtered out

    def test_create_system_prompt(self):
        """Test creating system prompt."""
        with patch("core.claude_client.settings", self.mock_settings):
            with patch("core.claude_client.boto3.client") as mock_boto:
                mock_boto.return_value = Mock()

                client = ClaudeClient()

                message = "What is Python?"
                conversation_context = "User: Hello"
                retrieved_context = "Python is a programming language."

                prompt = client.create_system_prompt(
                    message, conversation_context, retrieved_context
                )

                assert "SUSTEN AI" in prompt
                assert message in prompt
                assert conversation_context in prompt
                assert retrieved_context in prompt

    @pytest.mark.asyncio
    async def test_ask_with_context_stream_credential_error(self):
        """Test streaming with credential error."""
        settings_no_creds = Mock(spec=Settings)
        settings_no_creds.aws_access_key_id = None
        settings_no_creds.aws_secret_access_key = "test_secret"
        settings_no_creds.aws_region = "us-east-1"
        settings_no_creds.claude_model = "claude-3-sonnet-20240229"

        with patch("core.claude_client.settings", settings_no_creds):
            with patch("core.claude_client.boto3.client") as mock_boto:
                mock_boto.return_value = Mock()

                client = ClaudeClient()

                chunks = []
                async for chunk in client.ask_with_context_stream("Test message"):
                    chunks.append(chunk)

                assert len(chunks) == 1
                chunk_data = json.loads(chunks[0].split("data: ")[1].split("\n\n")[0])
                assert chunk_data["type"] == "error"
                assert "AWS credentials not configured" in chunk_data["text"]

    def test_dict_to_message(self):
        """Test converting dictionary to Message object."""
        timestamp_str = "2024-01-01T12:00:00"
        msg_dict = {
            "id": "msg1",
            "content": "Hello world",
            "sender": {"id": "user1", "name": "Test User"},
            "timestamp": timestamp_str,
            "isCurrentUser": True,
        }

        message = ClaudeClient.dict_to_message(msg_dict)

        assert message.id == "msg1"
        assert message.content == "Hello world"
        assert message.sender == {"id": "user1", "name": "Test User"}
        assert message.timestamp == datetime.fromisoformat(timestamp_str)
        assert message.isCurrentUser is True

    def test_dict_to_message_minimal(self):
        """Test converting minimal dictionary to Message object."""
        msg_dict = {}

        message = ClaudeClient.dict_to_message(msg_dict)

        assert message.id == ""
        assert message.content == ""
        assert message.sender == {}
        assert isinstance(message.timestamp, datetime)
        assert message.isCurrentUser is False


if __name__ == "__main__":
    pytest.main([__file__])
