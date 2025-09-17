"""
Claude AI client for AWS Bedrock integration.
"""

import boto3
import json
from typing import List, Dict, Any, Optional, AsyncGenerator, Tuple
from datetime import datetime
import asyncio
from botocore.exceptions import ClientError, NoCredentialsError
from .config import settings
from .exceptions import ExternalServiceError


class Message:
    """Message class for conversation history."""

    def __init__(
        self,
        id: str,
        content: str,
        sender: Dict[str, Any],
        timestamp: datetime,
        isCurrentUser: bool = False,
    ):
        self.id = id
        self.content = content
        self.sender = sender
        self.timestamp = timestamp
        self.isCurrentUser = isCurrentUser


class ClaudeClient:
    """AWS Bedrock Claude client for AI queries."""

    def __init__(self):
        """Initialize AWS Bedrock client for Claude queries."""
        self.region = settings.aws_region
        self.model_id = settings.claude_model
        self._initialized = False

        # Initialize AWS Bedrock client
        try:
            self.bedrock_client = boto3.client(
                "bedrock-runtime",
                region_name=self.region,
                aws_access_key_id=settings.aws_access_key_id,
                aws_secret_access_key=settings.aws_secret_access_key,
            )
        except Exception as e:
            print(f"Failed to initialize AWS Bedrock client: {e}")
            self.bedrock_client = None

    def initialize(self) -> bool:
        """Initialize Claude client."""
        try:
            print("🤖 Initializing Claude AI...")
            # Validate credentials during initialization
            is_valid, error_msg = self.validate_credentials()
            if not is_valid:
                print(f"❌ Failed to initialize Claude: {error_msg}")
                self._initialized = False
                return False

            print("✅ Claude AI configured")
            self._initialized = True
            return True
        except Exception as e:
            print(f"❌ Failed to initialize Claude: {e}")
            self._initialized = False
            return False

    def is_ready(self) -> bool:
        """Check if Claude client is ready."""
        return self._initialized and self.bedrock_client is not None

    def validate_credentials(self) -> tuple[bool, str]:
        """Validate AWS credentials are properly configured."""
        if not settings.aws_access_key_id or not settings.aws_secret_access_key:
            return (
                False,
                "AWS credentials not configured. Please set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY environment variables.",
            )

        if not self.bedrock_client:
            return False, "Failed to initialize AWS Bedrock client."

        return True, ""

    def build_conversation_context(
        self, conversation_history: List[Message], max_messages: int = 5
    ) -> str:
        """
        Build conversation context from message history.

        Args:
            conversation_history: List of Message objects
            max_messages: Maximum number of messages to include in context

        Returns:
            Formatted conversation context string
        """
        # Filter out AI assistant messages and keep only user messages
        user_messages = [
            msg for msg in conversation_history if msg.sender.get("id") != "susten-ai"
        ]

        # Keep last N messages for context
        recent_messages = (
            user_messages[-max_messages:]
            if len(user_messages) > max_messages
            else user_messages
        )

        # Format messages for context
        context_lines = [f"User: {msg.content}" for msg in recent_messages]

        return "\n".join(context_lines)

    def create_system_prompt(
        self, message: str, conversation_context: str = "", retrieved_context: str = ""
    ) -> str:
        """Create system prompt for SUSTEN AI Assistant."""
        return f"""あなたはSUSTEN AIアシスタントです。
        会話履歴：
        {conversation_context}
        以下は過去のFAQです。これを参考に、ユーザーの質問に答えてください。
        わからない場合はわからないと言ってください。親しみやすく、わかりやすい日本語で回答してください。
        {retrieved_context}
        ユーザーの質問: {message}
        答え:"""

    async def ask_with_context_stream(
        self,
        message: str,
        retrieved_context: str = "",
        top_k: int = 3,
        conversation_history: str = "",
    ) -> AsyncGenerator[str, None]:
        """
        Query Claude with streaming response.

        Args:
            message: User's current message
            retrieved_context: Retrieved context from RAG
            top_k: Number of similar FAQs to retrieve
            conversation_history: Pre-formatted conversation context string

        Yields:
            Streaming response chunks
        """
        try:
            # Validate credentials
            is_valid, error_msg = self.validate_credentials()
            if not is_valid:
                yield f"data: {json.dumps({'type': 'error', 'text': f'Query error: Claude query failed: {error_msg}', 'timestamp': datetime.now().isoformat()})}\n\n"
                return

            # Enhanced debugging output with emojis
            print("\n" + "=" * 60)
            print("🔍 DEBUG: RAG Context Retrieval")
            print("=" * 60)
            print(f"📝 User Query: {message}")
            print(f"🔢 Top-K: {top_k}")
            print("\n📚 Retrieved Passages:")
            print("-" * 60)

            # Split and format each passage
            passages = retrieved_context.split("\n\n")
            for i, passage in enumerate(passages, 1):
                if passage.strip():
                    print(f"\n📄 Passage {i}:")
                    print(passage)
                    print("-" * 40)

            print("\n" + "=" * 60 + "\n")

            # Create system prompt with both contexts
            system_prompt = self.create_system_prompt(
                message, conversation_history, retrieved_context
            )

            print(f"Using model: {self.model_id} in region: {self.region}")

            # Prepare the request body for Bedrock streaming
            request_body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 1000,
                "temperature": 0.7,
                "messages": [{"role": "user", "content": system_prompt}],
            }

            try:
                # Try to use streaming API first
                response = self.bedrock_client.invoke_model_with_response_stream(
                    modelId=self.model_id,
                    body=json.dumps(request_body),
                    contentType="application/json",
                )

                # Handle streaming response
                stream = response.get("body")
                if stream:
                    for event in stream:
                        chunk = event.get("chunk")
                        if chunk:
                            chunk_data = json.loads(chunk.get("bytes").decode())

                            if chunk_data.get("type") == "content_block_delta":
                                text = chunk_data.get("delta", {}).get("text", "")
                                if text:
                                    yield f"data: {json.dumps({'type': 'content', 'text': text, 'timestamp': datetime.now().isoformat()})}\n\n"
                                    await asyncio.sleep(
                                        0.01
                                    )  # Small delay for better UX

                            elif chunk_data.get("type") == "message_stop":
                                break

            except Exception as stream_error:
                print(
                    f"⚠️ Streaming failed, falling back to regular API: {stream_error}"
                )

                # Fallback to regular API
                response = self.bedrock_client.invoke_model(
                    modelId=self.model_id,
                    body=json.dumps(request_body),
                    contentType="application/json",
                )

                # Parse the response
                response_body = json.loads(response["body"].read())

                # Extract the answer from Claude's response
                answer = ""
                if "content" in response_body and len(response_body["content"]) > 0:
                    answer = response_body["content"][0].get("text", "")

                # Stream the response word by word with delay
                if answer:
                    words = answer.split()
                    for word in words:
                        yield f"data: {json.dumps({'type': 'content', 'text': word + ' ', 'timestamp': datetime.now().isoformat()})}\n\n"
                        # Add delay between words for streaming effect
                        await asyncio.sleep(0.05)  # 50ms delay between words

            # Send completion signal
            yield f"data: {json.dumps({'type': 'done', 'model': f'Claude ({self.model_id})', 'timestamp': datetime.now().isoformat()})}\n\n"

        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            error_message = e.response["Error"]["Message"]

            # Provide specific error messages based on error type
            if "credentials" in error_message.lower():
                error_msg = "AWS credentials are not properly configured. Please check your environment variables."
            elif "region" in error_message.lower():
                error_msg = "AWS region configuration issue. Please verify your AWS_REGION setting."
            elif (
                "model" in error_message.lower() or "ValidationException" in error_code
            ):
                error_msg = f"Model validation error: {error_message}. Please check your model ID configuration and AWS Bedrock model access."
            elif (
                "throttling" in error_message.lower() or "rate" in error_message.lower()
            ):
                error_msg = (
                    "Too many requests. Please wait a moment before trying again."
                )
            else:
                error_msg = f"AWS Bedrock error: {error_message}"

            yield f"data: {json.dumps({'type': 'error', 'text': f'Query error: Claude query failed: {error_msg}', 'timestamp': datetime.now().isoformat()})}\n\n"

        except NoCredentialsError:
            yield f"data: {json.dumps({'type': 'error', 'text': 'Query error: Claude query failed: AWS credentials not found. Please configure your AWS credentials.', 'timestamp': datetime.now().isoformat()})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'text': f'Query error: Claude query failed: Error streaming from Claude: {str(e)}', 'timestamp': datetime.now().isoformat()})}\n\n"

    @staticmethod
    def dict_to_message(msg_dict: Dict[str, Any]) -> Message:
        """Convert dictionary to Message object."""
        return Message(
            id=msg_dict.get("id", ""),
            content=msg_dict.get("content", ""),
            sender=msg_dict.get("sender", {}),
            timestamp=datetime.fromisoformat(
                msg_dict.get("timestamp", datetime.now().isoformat())
            ),
            isCurrentUser=msg_dict.get("isCurrentUser", False),
        )
