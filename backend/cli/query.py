#!/usr/bin/env python3
"""
RAG FAQ Bot - Interactive Query Interface
Intelligent Q&A Assistant powered by Claude AI and multilingual embeddings.
"""

import sys
import os
import asyncio
import json
from datetime import datetime
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.prompt import Prompt
from rich.columns import Columns
from rich.align import Align
from rich import box
from rich.live import Live
from rich.spinner import Spinner
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
import time

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.vector_store import VectorStore
from core.faq import FAQManager
from core.database import db_manager
from core.claude_client import ClaudeClient

console = Console()


class QueryInterface:
    """Interactive query interface with rich CLI styling"""

    def __init__(self):
        self.vector_store = None
        self.claude = None
        self.conversation_history = ""
        self.session_count = 0

    def clear_screen(self):
        """Clear the terminal screen"""
        console.clear()

    def print_banner(self):
        """Print a beautiful ASCII banner"""
        banner_text = """
🤖 FAQ Bot - Intelligent Q&A Assistant 🤖

Powered by Claude AI & Multilingual Embeddings
"""

        banner_panel = Panel(
            Align.center(Text(banner_text.strip(), style="bold cyan")),
            box=box.DOUBLE,
            border_style="bright_blue",
            padding=(1, 2),
        )

        console.print()
        console.print(banner_panel)
        console.print()

    def print_loading(self, message):
        """Print loading message with spinner"""
        with console.status(f"[bold yellow]{message}...", spinner="dots"):
            time.sleep(0.5)  # Brief pause for visual effect

    def print_success(self, message):
        """Print success message"""
        console.print(f"[bold green]✅ {message}[/bold green]")

    def print_error(self, message):
        """Print error message"""
        console.print(f"[bold red]❌ {message}[/bold red]")

    def print_info(self, message):
        """Print info message"""
        console.print(f"[bold blue]ℹ️  {message}[/bold blue]")

    def print_separator(self):
        """Print a separator line"""
        console.print("[dim]" + "─" * 80 + "[/dim]")

    def initialize_components(self):
        """Initialize vector store and Claude components"""
        try:
            # Initialize Claude AI
            self.print_loading("Initializing Claude AI")
            self.claude = ClaudeClient()
            self.print_success("Claude AI configured")

            # Initialize Vector Store
            self.print_loading("Loading multilingual embedding model")
            self.vector_store = VectorStore()
            self.print_success("Embedding model loaded")

            return True

        except Exception as e:
            self.print_error(f"Failed to initialize components: {e}")
            return False

    def load_faq_data(self):
        """Load FAQ data and check cache status"""
        try:
            # Check cache status
            cache_info = self.vector_store.get_cache_info()
            if cache_info["cached"]:
                self.print_success(
                    f"Found existing vector cache: {cache_info.get('document_count', 'unknown')} FAQs"
                )

                # Display cache metadata in a panel - cache_info itself contains the metadata
                cache_details = f"""📅 Created: {cache_info.get('created_at', 'unknown')}
🧠 Model: {cache_info.get('model_name', 'unknown')}
📁 Cache Dir: {cache_info.get('cache_dir', 'unknown')}
📏 Distance Metric: {cache_info.get('distance_metric', 'unknown')}"""

                console.print(
                    Panel(
                        cache_details,
                        title="Cache Information",
                        border_style="green",
                        padding=(0, 1),
                    )
                )
            else:
                self.print_info("No vector cache found - will build from scratch")

            # Initialize database and FAQ manager
            self.print_loading("Loading FAQ database")
            db_manager.initialize_schema()
            faq_manager = FAQManager(db_manager)

            # Get FAQs for vector store
            faqs = faq_manager.load_faqs_for_rag()
            faq_count = len(faqs)
            self.print_success(f"Loaded {faq_count} FAQ entries from database")

            # Create embeddings and index
            if cache_info["cached"]:
                self.print_loading("Loading vector store from cache")
                self.vector_store.initialize(faq_manager)
            else:
                self.print_loading(
                    "Building vector search index (this may take a while...)"
                )
                self.vector_store.initialize(faq_manager, faqs)

            # Get dimension from cache info
            dimension = cache_info.get("embedding_dimension", "unknown")
            self.print_success("Vector index ready")

            return True

        except Exception as e:
            self.print_error(f"Failed to load FAQ data: {e}")
            return False

    def print_chat_header(self):
        """Print chat interface header"""
        header_text = """💬 Interactive Chat Interface

Ask questions in Japanese or English. The bot will search through FAQ data to provide relevant answers.

Commands:
• Type 'exit', 'quit', or 'q' to end session
• Type 'clear' or 'cls' to clear screen
• Type 'help' for more information"""

        header_panel = Panel(
            header_text,
            title="Chat Interface",
            border_style="bright_blue",
            padding=(1, 2),
        )

        console.print(header_panel)
        console.print()

    def print_help(self):
        """Print help information"""
        help_text = """🆘 Help & Commands

[bold]Available Commands:[/bold]
• [cyan]exit, quit, q[/cyan] - End the chat session
• [cyan]clear, cls[/cyan] - Clear screen and reset conversation
• [cyan]help[/cyan] - Show this help message

[bold]Usage Tips:[/bold]
• Ask questions naturally in Japanese or English
• The bot searches FAQ database for relevant context
• Conversation history is maintained during the session
• Responses are generated using Claude AI with FAQ context

[bold]Examples:[/bold]
• "How do I reset my password?"
• "投資の始め方を教えてください"
• "What are the fees?"
• "サポートに連絡するには？"
"""

        help_panel = Panel(
            help_text, title="Help & Usage Guide", border_style="yellow", padding=(1, 2)
        )

        console.print(help_panel)

    def show_context(self, context):
        """Show the FAQ context used for the response"""
        if not context.strip():
            return

        # Format context nicely
        formatted_context = ""
        lines = context.split("\n")

        for line in lines:
            line = line.strip()
            if line.startswith("passage: Q:"):
                question = line.replace("passage: Q:", "").strip()
                formatted_context += f"❓ [bold]{question}[/bold]\n"
            elif line.startswith("A:"):
                answer = line.replace("A:", "").strip()
                formatted_context += f"💡 {answer}\n\n"

        if formatted_context:
            context_panel = Panel(
                formatted_context.strip(),
                title="📚 Referenced FAQ Context",
                border_style="dim",
                padding=(1, 2),
            )
            console.print(context_panel)

    async def _get_claude_response_streaming(self, user_input, context):
        """Get response from Claude with real-time streaming display"""
        response_chunks = []

        # Start the response display
        self.session_count += 1
        console.print()
        console.print(
            f"[bold green]🤖 AI Assistant - Response #{self.session_count}[/bold green]"
        )
        console.print("[dim]" + "─" * 60 + "[/dim]")

        # Create a text object that we'll update
        response_text = ""

        try:
            async for chunk in self.claude.ask_with_context_stream(
                message=user_input,
                retrieved_context=context,
                conversation_history=self.conversation_history,
            ):
                # Parse the streaming chunk
                if chunk.startswith("data: "):
                    try:
                        data = json.loads(chunk[6:])  # Remove "data: " prefix
                        if data.get("type") == "content":
                            chunk_text = data.get("text", "")
                            if chunk_text:
                                response_chunks.append(chunk_text)
                                response_text += chunk_text
                                # Print the new chunk without newline, with slight delay for readability
                                console.print(chunk_text, end="", style="white")
                                # Small delay to make streaming more readable
                                await asyncio.sleep(0.01)
                        elif data.get("type") == "error":
                            raise Exception(data.get("text", "Unknown error"))
                        elif data.get("type") == "done":
                            break
                    except json.JSONDecodeError:
                        continue

            # Add final newline and separator
            console.print()
            console.print("[dim]" + "─" * 60 + "[/dim]")

        except Exception as e:
            console.print(f"\n[red]❌ Error during streaming: {e}[/red]")
            raise

        return "".join(response_chunks)

    def process_query(self, user_input):
        """Process user query using vector search and Claude with streaming response"""
        try:
            # Show thinking indicator while searching
            with console.status(
                "[bold yellow]🔍 Searching knowledge base...",
                spinner="dots",
            ):
                # Search for relevant context
                context = self.vector_store.search_similar_faqs(user_input, top_k=3)

            # Show context if available (before streaming response)
            self.show_context(context)

            # Show streaming indicator
            console.print("[bold yellow]💭 Generating response...[/bold yellow]")

            # Generate response with streaming display
            response = asyncio.run(
                self._get_claude_response_streaming(user_input, context)
            )

            # Update conversation history (simple string format)
            self.conversation_history += (
                f"Human: {user_input}\nAssistant: {response}\n\n"
            )

            return True

        except Exception as e:
            self.print_error(f"Failed to generate response: {e}")
            return False

    def start_chat(self):
        """Start the interactive chat session"""
        self.print_chat_header()

        while True:
            try:
                # Get user input with nice formatting
                console.print()
                user_input = Prompt.ask("[bold cyan]You", default="")

                # Handle commands
                if user_input.lower() in ["exit", "quit", "q"]:
                    goodbye_panel = Panel(
                        "Thank you for using FAQ Bot! 👋",
                        title="Goodbye",
                        border_style="green",
                        padding=(1, 2),
                    )
                    console.print(goodbye_panel)
                    break

                if user_input.lower() in ["clear", "cls"]:
                    self.clear_screen()
                    self.print_banner()
                    self.print_chat_header()
                    self.conversation_history = ""
                    self.session_count = 0
                    continue

                if user_input.lower() == "help":
                    self.print_help()
                    continue

                if not user_input.strip():
                    console.print("[yellow]Please enter a question.[/yellow]")
                    continue

                # Process the query
                try:
                    self.process_query(user_input)
                except Exception as e:
                    self.print_error(f"An error occurred: {e}")

            except KeyboardInterrupt:
                goodbye_panel = Panel(
                    "Session interrupted. Goodbye! 👋",
                    title="Goodbye",
                    border_style="yellow",
                    padding=(1, 2),
                )
                console.print(goodbye_panel)
                break
            except Exception as e:
                self.print_error(f"An error occurred: {e}")

    def run(self):
        """Main entry point for the query interface"""
        self.clear_screen()
        self.print_banner()

        # Initialize components
        if not self.initialize_components():
            return 1

        # Load FAQ data
        if not self.load_faq_data():
            return 1

        self.print_success("System ready!")
        self.print_separator()

        # Start chat interface
        self.start_chat()

        return 0


def main():
    """Main function"""
    interface = QueryInterface()
    return interface.run()


if __name__ == "__main__":
    sys.exit(main())
