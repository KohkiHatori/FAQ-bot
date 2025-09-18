#!/usr/bin/env python3
"""
FAQ Database Management Tool
Provides CRUD operations for the FAQ database using FAQManager.
"""

import sys
import os
import csv
import json
from datetime import datetime
from typing import List, Optional
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.prompt import Confirm, Prompt
from rich.columns import Columns
from rich.align import Align
from rich import box
from rich.progress import track
import time

# Add the backend directory to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import from new architecture
from core.database import db_manager
from core.faq import FAQManager
from models import FAQCreateRequest, FAQUpdateRequest
from core.exceptions import FAQBotException

console = Console()

# Global FAQ manager instance
faq_manager = None


def get_faq_manager():
    """Get or create FAQ manager instance"""
    global faq_manager
    if faq_manager is None:
        try:
            # Initialize database
            db_manager.initialize_schema()
            # Create FAQ manager instance
            faq_manager = FAQManager(db_manager)
        except Exception as e:
            console.print(f"[red]❌ Failed to initialize FAQ manager: {e}[/red]")
            return None
    return faq_manager


def list_faqs(limit=None, status=None, category=None, tag=None):
    """List all FAQs with optional filtering"""
    manager = get_faq_manager()
    if not manager:
        return

    try:
        with console.status("[bold green]Loading FAQs..."):
            # Build filters for FAQManager
            filters = {}
            if limit:
                filters["limit"] = limit
            if status:
                filters["status"] = status
            if category:
                filters["category"] = category
            if tag:
                filters["tag"] = tag

            result = manager.get_faqs(**filters)
            faqs = result["faqs"]

        if not faqs:
            filter_text = (
                f" (filtered by {', '.join([f'{k}={v}' for k, v in [('status', status), ('category', category), ('tag', tag)] if v])})"
                if status or category or tag
                else ""
            )
            console.print(
                Panel(
                    f"[yellow]📭 No FAQs found in the database{filter_text}[/yellow]",
                    title="Empty Database",
                    border_style="yellow",
                )
            )
            return

        # Display FAQs as individual panels instead of a table for full content
        filter_info = f" (filtered)" if status or category or tag else ""
        console.print(
            f"[bold blue]📋 FAQ Database ({len(faqs)} entries{filter_info})[/bold blue]"
        )
        console.print()

        for faq in faqs:
            # Handle both string and datetime objects for created_at
            if faq.created_at:
                if isinstance(faq.created_at, str):
                    # Parse string format like "2025-06-20 08:36:04"
                    created_display = (
                        faq.created_at.split()[0]
                        if " " in faq.created_at
                        else faq.created_at
                    )
                else:
                    # Handle datetime object
                    created_display = faq.created_at.strftime("%Y-%m-%d")
            else:
                created_display = "N/A"

            # Create panel content with full question and answer
            panel_content = f"[bold cyan]ID: {faq.id}[/bold cyan] | [dim]Created: {created_display}[/dim]\n"
            panel_content += f"[bold yellow]Status:[/bold yellow] {faq.status} | [bold magenta]Category:[/bold magenta] {faq.category}\n"
            if faq.tags:
                panel_content += f"[bold blue]Tags:[/bold blue] {', '.join(faq.tags)}\n"
            panel_content += f"\n[bold green]Question:[/bold green]\n{faq.question}\n\n"
            panel_content += f"[bold white]Answer:[/bold white]\n{faq.answer}"

            # Color border based on status
            border_color = "green" if faq.status == "public" else "red"
            console.print(Panel(panel_content, border_style=border_color, expand=False))
            console.print()

    except FAQBotException as e:
        console.print(f"[red]❌ Error: {e}[/red]")


def search_faqs(query):
    """Search FAQs using FAQManager search functionality"""
    manager = get_faq_manager()
    if not manager:
        return

    try:
        with console.status(f"[bold green]Searching for '{query}'..."):
            results = manager.search_faqs(query, limit=20)

        if not results:
            console.print(
                Panel(
                    f"[yellow]🔍 No FAQs found matching '{query}'[/yellow]",
                    title="Search Results",
                    border_style="yellow",
                )
            )

            # Suggest alternative search strategies
            suggestions = f"\n[dim]💡 Search Tips:[/dim]\n"
            suggestions += (
                f"[dim]• Try shorter keywords (e.g., individual words)[/dim]\n"
            )
            suggestions += f"[dim]• Use partial terms or key phrases[/dim]\n"
            suggestions += (
                f"[dim]• Try both Japanese and English terms if applicable[/dim]"
            )

            console.print(
                Panel(suggestions, title="Search Suggestions", border_style="blue")
            )
            return

        # Display search results as individual panels for full content
        console.print(
            f"[bold magenta]🔍 Search Results for '{query}' ({len(results)} found)[/bold magenta]"
        )
        console.print()

        for faq in results:
            # Create panel content with full question and answer
            panel_content = f"[bold cyan]ID: {faq.id}[/bold cyan]\n"
            panel_content += f"[bold yellow]Status:[/bold yellow] {faq.status} | [bold magenta]Category:[/bold magenta] {faq.category}\n"
            if faq.tags:
                panel_content += f"[bold blue]Tags:[/bold blue] {', '.join(faq.tags)}\n"
            panel_content += f"\n[bold green]Question:[/bold green]\n{faq.question}\n\n"
            panel_content += f"[bold white]Answer:[/bold white]\n{faq.answer}"

            # Color border based on status
            border_color = "green" if faq.status == "public" else "red"
            console.print(Panel(panel_content, border_style=border_color, expand=False))
            console.print()

    except FAQBotException as e:
        console.print(f"[red]❌ Search failed: {e}[/red]")


def add_faq(question, answer, status="public", category="other", tags=None):
    """Add a new FAQ with optional status, category, and tags"""
    manager = get_faq_manager()
    if not manager:
        return

    try:
        # Validate status
        if status not in ["public", "private"]:
            console.print("[red]❌ Status must be 'public' or 'private'[/red]")
            return

        # Handle tags
        tags = tags or []

        with console.status("[bold green]Adding new FAQ..."):
            request = FAQCreateRequest(
                question=question.strip(),
                answer=answer.strip(),
                status=status,
                category=category,
                tags=tags,
            )
            faq = manager.create_faq(request)

        # Show success with the added FAQ
        panel_content = (
            f"[green]✅ Successfully added FAQ with ID: {faq.id}[/green]\n\n"
        )
        panel_content += f"[bold]Question:[/bold] {question}\n\n"
        panel_content += f"[bold]Answer:[/bold] {answer}\n\n"
        panel_content += f"[bold yellow]Status:[/bold yellow] {status} | [bold magenta]Category:[/bold magenta] {category}\n"
        if tags:
            panel_content += f"[bold blue]Tags:[/bold blue] {', '.join(tags)}"

        border_color = "green" if status == "public" else "red"
        console.print(
            Panel(panel_content, title="FAQ Added", border_style=border_color)
        )

    except FAQBotException as e:
        console.print(f"[red]❌ Failed to add FAQ: {e}[/red]")


def update_faq(
    faq_id, question=None, answer=None, status=None, category=None, tags=None
):
    """Update an existing FAQ including new columns"""
    manager = get_faq_manager()
    if not manager:
        return

    try:
        # Validate status if provided
        if status is not None and status not in ["public", "private"]:
            console.print("[red]❌ Status must be 'public' or 'private'[/red]")
            return

        # Get existing FAQ
        old_faq = manager.get_faq_by_id(faq_id)

        # Filter out None values for update request
        updates = {}
        if question is not None:
            updates["question"] = question.strip()
        if answer is not None:
            updates["answer"] = answer.strip()
        if status is not None:
            updates["status"] = status
        if category is not None:
            updates["category"] = category
        if tags is not None:
            updates["tags"] = tags

        if updates:
            with console.status("[bold green]Updating FAQ..."):
                request = FAQUpdateRequest(**updates)
                new_faq, _ = manager.update_faq(faq_id, request)

            panel_content = f"[green]✅ Updated FAQ ID: {faq_id}[/green]\n\n"

            if question:
                panel_content += f"[dim]Old Question:[/dim] {old_faq.question}\n"
                panel_content += (
                    f"[bold green]New Question:[/bold green] {new_faq.question}\n\n"
                )

            if answer:
                panel_content += f"[dim]Old Answer:[/dim] {old_faq.answer}\n"
                panel_content += (
                    f"[bold green]New Answer:[/bold green] {new_faq.answer}\n\n"
                )

            if status is not None:
                panel_content += f"[dim]Old Status:[/dim] {old_faq.status}\n"
                panel_content += (
                    f"[bold yellow]New Status:[/bold yellow] {new_faq.status}\n\n"
                )

            if category is not None:
                panel_content += f"[dim]Old Category:[/dim] {old_faq.category}\n"
                panel_content += (
                    f"[bold magenta]New Category:[/bold magenta] {new_faq.category}\n\n"
                )

            if tags is not None:
                old_tags_str = ", ".join(old_faq.tags) if old_faq.tags else "None"
                new_tags_str = ", ".join(new_faq.tags) if new_faq.tags else "None"
                panel_content += f"[dim]Old Tags:[/dim] {old_tags_str}\n"
                panel_content += f"[bold blue]New Tags:[/bold blue] {new_tags_str}"

            border_color = "green" if new_faq.status == "public" else "red"
            console.print(
                Panel(panel_content, title="FAQ Updated", border_style=border_color)
            )
        else:
            console.print("[yellow]❌ No updates provided[/yellow]")

    except FAQBotException as e:
        console.print(f"[red]❌ Failed to update FAQ: {e}[/red]")


def delete_faq(faq_id):
    """Delete an FAQ"""
    manager = get_faq_manager()
    if not manager:
        return

    try:
        # Get FAQ to be deleted
        faq = manager.get_faq_by_id(faq_id)

        # Show FAQ to be deleted
        panel_content = f"[bold red]FAQ to delete (ID: {faq_id}):[/bold red]\n\n"
        panel_content += f"[bold]Question:[/bold] {faq.question}\n\n"
        panel_content += f"[bold]Answer:[/bold] {faq.answer}\n\n"
        panel_content += f"[bold yellow]Status:[/bold yellow] {faq.status} | [bold magenta]Category:[/bold magenta] {faq.category}\n"
        if faq.tags:
            panel_content += f"[bold blue]Tags:[/bold blue] {', '.join(faq.tags)}"

        border_color = "green" if faq.status == "public" else "red"
        console.print(
            Panel(panel_content, title="⚠️  Confirm Deletion", border_style=border_color)
        )

        if Confirm.ask(
            "[red]Are you sure you want to delete this FAQ?[/red]", default=False
        ):
            with console.status("[bold red]Deleting FAQ..."):
                deleted_faq = manager.delete_faq(faq_id)

            console.print(f"[green]✅ Successfully deleted FAQ ID: {faq_id}[/green]")
        else:
            console.print("[yellow]❌ Delete cancelled[/yellow]")

    except FAQBotException as e:
        console.print(f"[red]❌ Failed to delete FAQ: {e}[/red]")


def get_stats():
    """Get database statistics using FAQManager"""
    manager = get_faq_manager()
    if not manager:
        return

    try:
        with console.status("[bold green]Calculating statistics..."):
            stats = manager.get_statistics()
            categories_result = manager.get_all_categories()

        # Create statistics panels
        stats_panels = []

        # Main stats
        main_stats = f"[bold blue]Total FAQs:[/bold blue] {stats['total_faqs']}\n"
        main_stats += (
            f"[bold green]Recent FAQs (7 days):[/bold green] {stats['recent_faqs']}\n"
        )
        main_stats += f"[bold yellow]Database Health:[/bold yellow] {'Good' if stats['total_faqs'] > 0 else 'Empty'}"

        stats_panels.append(Panel(main_stats, title="📊 Overview", border_style="blue"))

        # Status and categorization stats
        status_stats = f"[bold green]Public FAQs:[/bold green] {stats['public_faqs']}\n"
        status_stats += f"[bold red]Private FAQs:[/bold red] {stats['private_faqs']}\n"
        status_stats += (
            f"[bold blue]FAQs with Tags:[/bold blue] {stats['faqs_with_tags']}\n\n"
        )
        status_stats += f"[bold]Top Categories:[/bold]\n"
        for category in categories_result["categories"][:5]:  # Show top 5 categories
            status_stats += f"  {category['name']}: {category['count']}\n"

        stats_panels.append(
            Panel(status_stats, title="📂 Content Organization", border_style="magenta")
        )

        # Length stats
        length_stats = f"[bold]Question Length:[/bold]\n"
        length_stats += f"  Average: {stats['avg_question_length']:.1f} chars\n\n"
        length_stats += f"[bold]Answer Length:[/bold]\n"
        length_stats += f"  Average: {stats['avg_answer_length']:.1f} chars"

        stats_panels.append(
            Panel(length_stats, title="📏 Content Analysis", border_style="green")
        )

        console.print(Columns(stats_panels))

    except FAQBotException as e:
        console.print(f"[red]❌ Failed to get statistics: {e}[/red]")


def get_all_tags():
    """Get all unique tags from the database"""
    manager = get_faq_manager()
    if not manager:
        return

    try:
        result = manager.get_all_tags()
        tags = result["tags"]

        if not tags:
            console.print(
                Panel(
                    "[yellow]📭 No tags found in the database[/yellow]",
                    title="🏷️ All Tags",
                    border_style="yellow",
                )
            )
        else:
            # Create tag display
            tag_content = f"[bold blue]Total Tags: {result['count']}[/bold blue]\n\n"
            tag_list = [f"[cyan]{tag}[/cyan]" for tag in tags]
            tag_content += ", ".join(tag_list)

            console.print(
                Panel(
                    tag_content,
                    title="🏷️ All Tags",
                    border_style="blue",
                    expand=False,
                )
            )

    except FAQBotException as e:
        console.print(f"[red]❌ Failed to get tags: {e}[/red]")


def get_all_categories():
    """Get all unique categories from the database"""
    manager = get_faq_manager()
    if not manager:
        return

    try:
        result = manager.get_all_categories()
        categories = result["categories"]

        if not categories:
            console.print(
                Panel(
                    "[yellow]📭 No categories found in the database[/yellow]",
                    title="📂 All Categories",
                    border_style="yellow",
                )
            )
        else:
            # Create category display
            category_content = f"[bold blue]Total Categories: {result['total_categories']}[/bold blue]\n\n"

            category_lines = []
            for category in categories:
                category_lines.append(
                    f"[green]{category['name']}[/green]: [bold]{category['count']}[/bold] FAQs"
                )

            category_content += "\n".join(category_lines)

            console.print(
                Panel(
                    category_content,
                    title="📂 All Categories",
                    border_style="green",
                    expand=False,
                )
            )

    except FAQBotException as e:
        console.print(f"[red]❌ Failed to get categories: {e}[/red]")


def show_help():
    """Show help information"""
    help_text = """
[bold blue]FAQ Database Management Tool[/bold blue]

[bold green]Available Commands:[/bold green]

        [bold]list[/bold] [dim][limit] [--status public|private] [--category <category>] [--tag|--tags <tag>][/dim]
    List all FAQs with optional filtering
    Example: python manage_faqs.py list 10
    Example: python manage_faqs.py list --status public --category investment
    Example: python manage_faqs.py list 5 --status private
            Example: python manage_faqs.py list --tag login (or --tags login)

[bold]search[/bold] [red]<query>[/red]
    Search FAQs using full-text search (includes question, answer, category, and tags)
    Example: python manage_faqs.py search "password"

[bold]add[/bold] [red]'<question>' '<answer>'[/red] [dim][--status public|private] [--category <category>] [--tags tag1,tag2][/dim]
    Add a new FAQ entry with optional metadata
    Example: python manage_faqs.py add 'How to login?' 'Use your email and password' --status public --category account --tags login,password

[bold]update[/bold] [red]<id>[/red] [dim][--question '<question>'] [--answer '<answer>'] [--status public|private] [--category <category>] [--tags tag1,tag2][/dim]
    Update an existing FAQ including metadata
    Example: python manage_faqs.py update 1 --question 'New question?' --status private --category advanced

[bold]delete[/bold] [red]<id>[/red]
    Delete an FAQ (with confirmation)
    Example: python manage_faqs.py delete 1

[bold]stats[/bold]
    Show database statistics including status, category, and tag analytics
    Example: python manage_faqs.py stats

[bold]tags[/bold]
    List all unique tags in the database with counts
    Example: python manage_faqs.py tags

[bold]categories[/bold]
    List all unique categories in the database with counts
    Example: python manage_faqs.py categories

[bold]sync[/bold] [red]<csv_file>[/red]
    Sync FAQ data from CSV file to database
    Creates database and table structure if they don't exist
    Updates existing questions or creates new ones
    Example: python manage_faqs.py sync faq_data.csv

[bold yellow]New Column Features:[/bold yellow]
• [bold]Status:[/bold] 'public' (default) or 'private' - controls visibility in RAG system
• [bold]Category:[/bold] Flexible categorization (default: 'other')
• [bold]Tags:[/bold] Multiple tags per FAQ for enhanced search and organization
    """

    console.print(Panel(help_text, title="🚀 Help", border_style="cyan"))


def sync_from_csv(csv_file_path):
    """Sync FAQ data from CSV file to database using FAQManager"""
    manager = get_faq_manager()
    if not manager:
        return

    try:
        # Check if CSV file exists
        if not os.path.exists(csv_file_path):
            console.print(f"[red]❌ CSV file not found: {csv_file_path}[/red]")
            return

        with console.status(f"[bold green]Reading CSV file '{csv_file_path}'..."):
            # Read CSV file
            csv_data = []
            with open(csv_file_path, "r", encoding="utf-8") as file:
                csv_reader = csv.DictReader(file)

                # Check if required columns exist
                if (
                    "question" not in csv_reader.fieldnames
                    or "answer" not in csv_reader.fieldnames
                ):
                    console.print(
                        "[red]❌ CSV file must have 'question' and 'answer' columns[/red]"
                    )
                    return

                for row in csv_reader:
                    question = row["question"].strip()
                    answer = row["answer"].strip()

                    if question and answer:  # Skip empty rows
                        # Get optional columns with defaults
                        status = row.get("status", "public").strip() or "public"
                        category = row.get("category", "other").strip() or "other"
                        tags_str = row.get("tags", "").strip()
                        tags = (
                            [tag.strip() for tag in tags_str.split(",") if tag.strip()]
                            if tags_str
                            else []
                        )

                        csv_data.append(
                            {
                                "question": question,
                                "answer": answer,
                                "status": status,
                                "category": category,
                                "tags": tags,
                            }
                        )

        if not csv_data:
            console.print("[yellow]⚠️  No valid FAQ data found in CSV file[/yellow]")
            return

        console.print(f"[blue]📁 Found {len(csv_data)} FAQ entries in CSV file[/blue]")
        console.print()

        # Process each FAQ entry
        stats = {"updated": 0, "created": 0, "skipped": 0, "errors": 0}

        for entry in track(csv_data, description="Syncing FAQs"):
            try:
                question = entry["question"]
                answer = entry["answer"]
                status = entry["status"]
                category = entry["category"]
                tags = entry["tags"]

                # Check if question already exists using search
                existing_faqs = manager.search_faqs(question, limit=50)
                existing_faq = None

                # Look for exact question match
                for faq in existing_faqs:
                    if faq.question.strip().lower() == question.strip().lower():
                        existing_faq = faq
                        break

                if existing_faq:
                    # Compare answers (normalize whitespace for comparison)
                    if (
                        existing_faq.answer.strip() != answer.strip()
                        or existing_faq.status != status
                        or existing_faq.category != category
                        or set(existing_faq.tags) != set(tags)
                    ):

                        # Update existing FAQ
                        update_request = FAQUpdateRequest(
                            question=question,
                            answer=answer,
                            status=status,
                            category=category,
                            tags=tags,
                        )

                        updated_faq, old_faq = manager.update_faq(
                            existing_faq.id, update_request
                        )
                        stats["updated"] += 1

                        # Show update info
                        panel_content = (
                            f"[yellow]🔄 Updated FAQ ID: {existing_faq.id}[/yellow]\n\n"
                        )
                        panel_content += f"[bold]Question:[/bold] {question[:100]}{'...' if len(question) > 100 else ''}\n\n"
                        panel_content += f"[dim]Old Answer:[/dim] {old_faq.answer[:150]}{'...' if len(old_faq.answer) > 150 else ''}\n\n"
                        panel_content += f"[bold green]New Answer:[/bold green] {answer[:150]}{'...' if len(answer) > 150 else ''}"

                        console.print(
                            Panel(panel_content, border_style="yellow", expand=False)
                        )
                        console.print()
                    else:
                        stats["skipped"] += 1
                else:
                    # Create new FAQ
                    create_request = FAQCreateRequest(
                        question=question,
                        answer=answer,
                        status=status,
                        category=category,
                        tags=tags,
                    )

                    new_faq = manager.create_faq(create_request)
                    stats["created"] += 1

                    # Show creation info
                    panel_content = (
                        f"[green]✅ Created new FAQ ID: {new_faq.id}[/green]\n\n"
                    )
                    panel_content += f"[bold]Question:[/bold] {question[:100]}{'...' if len(question) > 100 else ''}\n\n"
                    panel_content += f"[bold]Answer:[/bold] {answer[:150]}{'...' if len(answer) > 150 else ''}"
                    if status != "public":
                        panel_content += f"\n[dim]Status:[/dim] {status}"
                    if category != "other":
                        panel_content += f"\n[dim]Category:[/dim] {category}"
                    if tags:
                        panel_content += f"\n[dim]Tags:[/dim] {', '.join(tags)}"

                    console.print(
                        Panel(panel_content, border_style="green", expand=False)
                    )
                    console.print()

            except Exception as e:
                stats["errors"] += 1
                console.print(f"[red]❌ Error processing FAQ: {e}[/red]")
                continue

        # Display final statistics
        console.print()
        stats_text = f"""[bold green]✅ CSV sync completed![/bold green]

📊 [bold]Statistics:[/bold]
• [green]Created:[/green] {stats['created']} new FAQs
• [yellow]Updated:[/yellow] {stats['updated']} existing FAQs
• [blue]Skipped:[/blue] {stats['skipped']} unchanged FAQs
• [red]Errors:[/red] {stats['errors']} failed entries
• [bold]Total processed:[/bold] {stats['created'] + stats['updated'] + stats['skipped']} entries

💾 All changes have been saved to the database.
🔄 Vector cache will need to be rebuilt for search functionality."""

        console.print(Panel(stats_text, title="🎯 Sync Results", border_style="green"))

        # Suggest cache rebuild if there were changes
        if stats["created"] > 0 or stats["updated"] > 0:
            console.print()
            console.print(
                "[yellow]💡 Tip: Run 'python cli/manage_cache.py build' to update the vector search cache[/yellow]"
            )

    except FileNotFoundError:
        console.print(f"[red]❌ CSV file not found: {csv_file_path}[/red]")
    except Exception as e:
        console.print(f"[red]❌ Failed to sync CSV data: {e}[/red]")


def main():
    # Show header
    header = Text("FAQ Database Management Tool", style="bold magenta")
    console.print(Align.center(header))
    console.print()

    if len(sys.argv) < 2:
        show_help()
        return

    command = sys.argv[1].lower()

    if command == "list":
        limit = None
        status = None
        category = None
        tag = None

        # Parse arguments for list command
        i = 2
        while i < len(sys.argv):
            if sys.argv[i] == "--status" and i + 1 < len(sys.argv):
                status = sys.argv[i + 1]
                i += 2
            elif sys.argv[i] == "--category" and i + 1 < len(sys.argv):
                category = sys.argv[i + 1]
                i += 2
            elif sys.argv[i] in ["--tag", "--tags"] and i + 1 < len(sys.argv):
                tag = sys.argv[i + 1]
                i += 2
            elif sys.argv[i].isdigit():  # If it's a number, it's the limit
                limit = int(sys.argv[i])
                i += 1
            else:
                i += 1

        list_faqs(limit, status, category, tag)

    elif command == "search":
        if len(sys.argv) < 3:
            console.print("[red]❌ Please provide a search query[/red]")
            return
        query = sys.argv[2]
        search_faqs(query)

    elif command == "add":
        if len(sys.argv) < 4:
            console.print("[red]❌ Please provide both question and answer[/red]")
            return
        question = sys.argv[2]
        answer = sys.argv[3]
        status = "public"
        category = "other"
        tags = None

        # Parse optional arguments
        i = 4
        while i < len(sys.argv):
            if sys.argv[i] == "--status" and i + 1 < len(sys.argv):
                status = sys.argv[i + 1]
                i += 2
            elif sys.argv[i] == "--category" and i + 1 < len(sys.argv):
                category = sys.argv[i + 1]
                i += 2
            elif sys.argv[i] == "--tags" and i + 1 < len(sys.argv):
                tags = sys.argv[i + 1].split(",") if sys.argv[i + 1] else []
                i += 2
            else:
                i += 1

        add_faq(question, answer, status, category, tags)

    elif command == "update":
        if len(sys.argv) < 3:
            console.print("[red]❌ Please provide FAQ ID[/red]")
            return

        try:
            faq_id = int(sys.argv[2])
        except ValueError:
            console.print("[red]❌ FAQ ID must be a number[/red]")
            return

        question = None
        answer = None
        status = None
        category = None
        tags = None

        # Parse optional arguments
        i = 3
        while i < len(sys.argv):
            if sys.argv[i] == "--question" and i + 1 < len(sys.argv):
                question = sys.argv[i + 1]
                i += 2
            elif sys.argv[i] == "--answer" and i + 1 < len(sys.argv):
                answer = sys.argv[i + 1]
                i += 2
            elif sys.argv[i] == "--status" and i + 1 < len(sys.argv):
                status = sys.argv[i + 1]
                i += 2
            elif sys.argv[i] == "--category" and i + 1 < len(sys.argv):
                category = sys.argv[i + 1]
                i += 2
            elif sys.argv[i] == "--tags" and i + 1 < len(sys.argv):
                tags = sys.argv[i + 1].split(",") if sys.argv[i + 1] else []
                i += 2
            else:
                i += 1

        update_faq(faq_id, question, answer, status, category, tags)

    elif command == "delete":
        if len(sys.argv) < 3:
            console.print("[red]❌ Please provide FAQ ID[/red]")
            return
        try:
            faq_id = int(sys.argv[2])
        except ValueError:
            console.print("[red]❌ FAQ ID must be a number[/red]")
            return
        delete_faq(faq_id)

    elif command == "stats":
        get_stats()

    elif command == "tags":
        get_all_tags()

    elif command == "categories":
        get_all_categories()

    elif command == "sync":
        if len(sys.argv) < 3:
            console.print("[red]❌ Please provide CSV file path[/red]")
            return
        csv_file_path = sys.argv[2]
        sync_from_csv(csv_file_path)

    elif command in ["help", "--help", "-h"]:
        show_help()

    else:
        console.print(f"[red]❌ Unknown command: {command}[/red]")
        console.print("[dim]Use 'help' to see available commands[/dim]")


if __name__ == "__main__":
    main()
