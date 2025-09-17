#!/usr/bin/env python3
"""
RAG Cache Management CLI Tool

This tool provides comprehensive management of the RAG (Retrieval-Augmented Generation) cache,
including viewing cache status, rebuilding, clearing, and testing the cache system.
"""

import sys
import os
import json
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.align import Align
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Confirm, Prompt

# Add parent directory to path to import new components
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.vector_store import VectorStore
from core.faq import FAQManager
from core.database import db_manager
from core.pending_changes import PendingChangesManager

console = Console()


def get_cache_status():
    """Display comprehensive cache status information"""
    try:
        vector_store = VectorStore()
        cache_info = vector_store.get_cache_info()

        # Also check pending changes
        pending_manager = PendingChangesManager()
        pending_info = pending_manager.get_pending_changes()

        if not cache_info["cached"]:
            console.print(
                Panel(
                    "[yellow]📭 No vector cache found[/yellow]\n\n"
                    "The vector cache has not been created yet or has been cleared.\n"
                    "Use 'build' command to create the cache from the FAQ database.",
                    title="🔍 Cache Status",
                    border_style="yellow",
                )
            )
            return

        # The cache_info itself contains the metadata
        metadata = cache_info

        # Create status table
        status_table = Table(show_header=False, box=None, padding=(0, 1))
        status_table.add_column("Field", style="bold cyan", width=20)
        status_table.add_column("Value", style="white")

        status_table.add_row(
            "📊 FAQ Count", str(metadata.get("document_count", "Unknown"))
        )
        status_table.add_row("🧠 Model", metadata.get("model_name", "Unknown"))
        status_table.add_row(
            "📐 Dimensions", str(metadata.get("embedding_dimension", "Unknown"))
        )
        status_table.add_row("🕒 Created", metadata.get("created_at", "Unknown"))
        status_table.add_row("📁 Cache Dir", metadata.get("cache_dir", "Unknown"))
        status_table.add_row(
            "📏 Distance Metric", metadata.get("distance_metric", "Unknown")
        )

        # Check cache files
        cache_paths = vector_store._get_cache_paths()
        files_table = Table(show_header=True, box=None, padding=(0, 1))
        files_table.add_column("File", style="bold")
        files_table.add_column("Status", justify="center")
        files_table.add_column("Size", justify="right")

        for file_key, file_path in cache_paths.items():
            if os.path.exists(file_path):
                size = os.path.getsize(file_path)
                size_str = format_file_size(size)
                files_table.add_row(
                    file_key.replace("_", " ").title(),
                    "[green]✅ Exists[/green]",
                    size_str,
                )
            else:
                files_table.add_row(
                    file_key.replace("_", " ").title(), "[red]❌ Missing[/red]", "N/A"
                )

        # Display information
        console.print(
            Panel(
                status_table,
                title="🔍 Cache Status - Active",
                border_style="green",
            )
        )

        console.print(
            Panel(
                files_table,
                title="📁 Cache Files",
                border_style="blue",
            )
        )

        # Show pending changes if any
        if pending_info["has_pending"]:
            pending_table = Table(show_header=True, box=None, padding=(0, 1))
            pending_table.add_column("FAQ ID", style="bold yellow", width=8)
            pending_table.add_column("Change", style="bold", width=10)
            pending_table.add_column("Original Status", width=12)
            pending_table.add_column("Timestamp", style="dim")

            for change in pending_info["changes"][:10]:  # Show first 10
                status_display = change["original_status"] or "N/A"
                pending_table.add_row(
                    str(change["faq_id"]),
                    change["change_type"].upper(),
                    status_display,
                    change["timestamp"][:19].replace("T", " "),
                )

            stats = pending_info["stats"]
            stats_text = f"📊 Total: {pending_info['total_count']} | Created: {stats['created']} | Updated: {stats['updated']} | Deleted: {stats['deleted']}"

            if pending_info["total_count"] > 10:
                stats_text += f"\n\n[dim]Showing first 10 of {pending_info['total_count']} pending changes[/dim]"

            console.print(
                Panel(
                    f"{stats_text}\n\n{pending_table}",
                    title="⏳ Pending Changes",
                    border_style="yellow",
                )
            )
        else:
            console.print(
                Panel(
                    "[green]✅ No pending changes[/green]\n\nAll FAQ changes have been processed.",
                    title="⏳ Pending Changes",
                    border_style="green",
                )
            )

    except Exception as e:
        console.print(f"[red]❌ Failed to get cache status: {e}[/red]")


def build_cache():
    """Build or rebuild the vector cache"""
    try:
        # Initialize components
        db_manager.initialize_schema()
        faq_manager = FAQManager(db_manager)
        vector_store = VectorStore()

        # Check if cache exists and warn about overwrite
        cache_info = vector_store.get_cache_info()
        if cache_info["cached"]:
            if not Confirm.ask(
                "[yellow]⚠️  Cache already exists. Rebuild anyway?[/yellow]",
                default=False,
            ):
                console.print("[dim]Cache build cancelled.[/dim]")
                return

        console.print("[blue]🔄 Building vector cache...[/blue]")

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:

            # Load FAQ data
            task1 = progress.add_task("Loading FAQ data from database...", start=False)
            progress.start_task(task1)

            # Get FAQs from database
            faqs = faq_manager.load_faqs_for_rag()
            faq_count = len(faqs)

            progress.update(task1, description=f"✅ Loaded {faq_count} FAQs")
            progress.stop_task(task1)

            if faq_count == 0:
                console.print(
                    "[red]❌ No FAQs found in database. Cannot build cache.[/red]"
                )
                return

            # Create embeddings and index
            task2 = progress.add_task(
                "Creating embeddings and FAISS index...", start=False
            )
            progress.start_task(task2)

            result = vector_store.rebuild_cache(faq_manager)

            # Get dimension from cache info after rebuild
            cache_info = vector_store.get_cache_info()
            dimension = cache_info.get("embedding_dimension", "Unknown")

            progress.update(
                task2, description=f"✅ Built index with {dimension} dimensions"
            )
            progress.stop_task(task2)

        # Show success message
        console.print(
            Panel(
                f"[green]✅ Vector cache successfully built![/green]\n\n"
                f"📊 Processed: {faq_count} FAQs\n"
                f"📐 Dimensions: {dimension}\n"
                f"🧠 Model: {vector_store.model_name}\n"
                f"📏 Distance Metric: {vector_store.distance_metric}\n\n"
                f"The cache is now ready for use in the FAQ bot.",
                title="🎯 Build Complete",
                border_style="green",
            )
        )

    except Exception as e:
        console.print(f"[red]❌ Failed to build cache: {e}[/red]")


def show_pending_changes():
    """Show detailed pending changes information"""
    try:
        pending_manager = PendingChangesManager()
        pending_info = pending_manager.get_pending_changes()

        if not pending_info["has_pending"]:
            console.print(
                Panel(
                    "[green]✅ No pending changes found![/green]\n\n"
                    "All FAQ changes have been processed and embedded in the vector cache.\n"
                    "The cache is up to date with the database.",
                    title="⏳ Pending Changes",
                    border_style="green",
                )
            )
            return

        # Summary statistics
        stats = pending_info["stats"]
        summary_table = Table(show_header=False, box=None, padding=(0, 2))
        summary_table.add_column("Metric", style="bold cyan", width=15)
        summary_table.add_column("Count", style="bold white", justify="right")

        summary_table.add_row("📊 Total", str(pending_info["total_count"]))
        summary_table.add_row("🆕 Created", str(stats["created"]))
        summary_table.add_row("✏️  Updated", str(stats["updated"]))
        summary_table.add_row("🗑️  Deleted", str(stats["deleted"]))

        console.print(
            Panel(
                summary_table,
                title="📊 Pending Changes Summary",
                border_style="yellow",
            )
        )

        # Detailed changes table
        changes_table = Table(show_header=True, box=None, padding=(0, 1))
        changes_table.add_column("FAQ ID", style="bold yellow", width=8)
        changes_table.add_column("Change Type", style="bold", width=12)
        changes_table.add_column("Original Status", width=15)
        changes_table.add_column("Timestamp", style="dim", width=20)

        for change in pending_info["changes"]:
            change_type = change["change_type"].upper()
            status_display = change["original_status"] or "N/A"
            timestamp_display = change["timestamp"][:19].replace("T", " ")

            # Color code change types
            if change_type == "CREATED":
                change_type = f"[green]{change_type}[/green]"
            elif change_type == "UPDATED":
                change_type = f"[blue]{change_type}[/blue]"
            elif change_type == "DELETED":
                change_type = f"[red]{change_type}[/red]"

            changes_table.add_row(
                str(change["faq_id"]), change_type, status_display, timestamp_display
            )

        console.print(
            Panel(
                changes_table,
                title="📋 Detailed Pending Changes",
                border_style="blue",
            )
        )

        console.print(
            Panel(
                "[yellow]💡 To process these changes:[/yellow]\n\n"
                "1. Run [bold]'rebuild'[/bold] command to update the vector cache\n"
                "2. This will embed new/updated FAQs and restore their proper status\n"
                "3. Deleted FAQs will be removed from the cache\n\n"
                "[dim]Note: FAQs with pending changes are temporarily marked as 'pending' status[/dim]",
                title="🔧 Next Steps",
                border_style="cyan",
            )
        )

    except Exception as e:
        console.print(f"[red]❌ Failed to get pending changes: {e}[/red]")


def test_cache():
    """Test the vector cache functionality"""
    try:
        vector_store = VectorStore()
        cache_info = vector_store.get_cache_info()

        if not cache_info["cached"]:
            console.print(
                "[red]❌ No cache found. Build the cache first using 'build' command.[/red]"
            )
            return

        console.print("[blue]🧪 Testing vector cache functionality...[/blue]")

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:

            # Load cache
            task1 = progress.add_task("Loading cache...", start=False)
            progress.start_task(task1)

            # Initialize database and FAQ manager
            db_manager.initialize_schema()
            faq_manager = FAQManager(db_manager)

            vector_store.initialize(faq_manager)  # Load from cache
            # Get dimension from cache info
            cache_info = vector_store.get_cache_info()
            dimension = cache_info.get("embedding_dimension", "Unknown")
            progress.update(task1, description="✅ Cache loaded successfully")
            progress.stop_task(task1)

        # Get test query from user
        console.print()
        test_query = Prompt.ask(
            "[bold cyan]Enter a test query[/bold cyan]", default="ログイン"
        )

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            # Test search
            task2 = progress.add_task("Testing search functionality...", start=False)
            progress.start_task(task2)

            results = vector_store.search_similar_faqs(test_query, top_k=2)

            progress.update(task2, description="✅ Search test completed")
            progress.stop_task(task2)

        # Display test results
        result_count = len(results.split("passage:")) - 1 if results else 0
        console.print(
            Panel(
                f"[green]✅ Cache test successful![/green]\n\n"
                f"📊 Loaded: {len(vector_store.document_texts)} FAQs\n"
                f"📐 Dimensions: {dimension}\n"
                f"🔍 Test query: '{test_query}'\n"
                f"📝 Results: {result_count} passages retrieved\n"
                f"📏 Distance Metric: {vector_store.distance_metric}\n\n"
                f"The vector cache is working correctly and ready for use.",
                title="🧪 Test Results",
                border_style="green",
            )
        )

        # Show sample results
        if results:
            console.print(
                Panel(
                    f"[dim]{results[:500]}{'...' if len(results) > 500 else ''}[/dim]",
                    title="📄 Sample Retrieved Context",
                    border_style="blue",
                )
            )

    except Exception as e:
        console.print(f"[red]❌ Cache test failed: {e}[/red]")


def show_help():
    """Show help information"""
    help_text = """
[bold blue]Vector Cache Management Tool[/bold blue]

[bold green]Available Commands:[/bold green]

[bold]status[/bold]
    Show comprehensive cache status including metadata, file information, and pending changes
    Example: python manage_cache.py status

[bold]pending[/bold]
    Show detailed pending changes that need to be processed
    Example: python manage_cache.py pending

[bold]build[/bold]
    Build or rebuild the vector cache from the FAQ database and process pending changes
    Example: python manage_cache.py build

[bold]test[/bold]
    Test the vector cache functionality with a custom query
    You will be prompted to enter a test query (default: ログイン)
    Example: python manage_cache.py test

[bold yellow]Pending Changes System:[/bold yellow]
• [bold]Tracking:[/bold] FAQs with pending changes are marked as 'pending' status
• [bold]Storage:[/bold] Changes tracked in rag_cache/pending_changes.json
• [bold]Processing:[/bold] Run 'build' to embed changes and restore proper status
• [bold]Types:[/bold] Created, Updated, Deleted FAQs

[bold yellow]Cache Information:[/bold yellow]
• [bold]Location:[/bold] rag_cache/ directory
• [bold]Files:[/bold] FAQ data, embeddings, FAISS index, metadata, pending changes
• [bold]Model:[/bold] multilingual-e5-small (default)
• [bold]Distance Metric:[/bold] L2 (default) or cosine similarity
• [bold]Content:[/bold] All FAQs from the database

[bold yellow]Workflow:[/bold yellow]
1. Check status: [cyan]python manage_cache.py status[/cyan]
2. View pending: [cyan]python manage_cache.py pending[/cyan]
3. Build cache: [cyan]python manage_cache.py build[/cyan]
4. Test cache: [cyan]python manage_cache.py test[/cyan]
    """

    console.print(Panel(help_text, title="🚀 Help", border_style="cyan"))


def format_file_size(size_bytes):
    """Format file size in human readable format"""
    if size_bytes == 0:
        return "0 B"

    size_names = ["B", "KB", "MB", "GB"]
    import math

    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return f"{s} {size_names[i]}"


def main():
    # Show header
    header = Text("Vector Cache Management Tool", style="bold magenta")
    console.print(Align.center(header))
    console.print()

    if len(sys.argv) < 2:
        show_help()
        return

    command = sys.argv[1].lower()

    if command == "status":
        get_cache_status()

    elif command == "pending":
        show_pending_changes()

    elif command == "build":
        build_cache()

    elif command == "test":
        test_cache()

    elif command in ["help", "--help", "-h"]:
        show_help()

    else:
        console.print(f"[red]❌ Unknown command: {command}[/red]")
        console.print("[dim]Use 'help' to see available commands[/dim]")


if __name__ == "__main__":
    main()
