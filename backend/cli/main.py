#!/usr/bin/env python3
"""
Susten FAQ Bot - Unified CLI Management Interface

This is the main CLI interface that provides access to all management tools
for the Susten FAQ Bot system, including FAQ management, cache management,
and interactive query interface.
"""

import sys
import os
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.align import Align
from rich.table import Table
from rich.columns import Columns
from rich.prompt import Prompt, Confirm
import subprocess

console = Console()


def show_main_menu():
    """Display the main menu with all available tools"""

    # Create tool cards
    tools = [
        {
            "name": "FAQ Management",
            "icon": "📋",
            "command": "manage_faqs.py",
            "description": "Manage FAQ database entries, search, add, update, delete FAQs",
            "features": [
                "List & filter FAQs",
                "Search FAQs",
                "Add/Update/Delete",
                "Statistics",
                "CSV sync",
            ],
        },
        {
            "name": "Cache Management",
            "icon": "🔄",
            "command": "manage_cache.py",
            "description": "Manage vector cache for optimal performance",
            "features": [
                "Cache status",
                "Build/Rebuild cache",
                "Clear cache",
                "Test cache",
            ],
        },
        {
            "name": "Interactive Query",
            "icon": "💬",
            "command": "query.py",
            "description": "Interactive Q&A interface with the FAQ bot",
            "features": [
                "Ask questions",
                "Get AI responses",
                "Context display",
                "Session history",
            ],
        },
    ]

    # Create cards for each tool
    cards = []
    for i, tool in enumerate(tools, 1):
        features_text = "\n".join([f"• {feature}" for feature in tool["features"]])

        card_content = f"""[bold cyan]{tool['icon']} {tool['name']}[/bold cyan]

{tool['description']}

[bold]Features:[/bold]
{features_text}

[dim]Command: {i}[/dim]"""

        cards.append(Panel(card_content, border_style="blue", padding=(1, 2)))

    console.print(
        Panel(
            Columns(cards, equal=True, expand=True),
            title="🚀 Susten FAQ Bot - CLI Management Tools",
            border_style="magenta",
            padding=(1, 2),
        )
    )

    return tools


def show_quick_actions():
    """Show quick action menu"""
    actions_table = Table(show_header=False, box=None, padding=(0, 2))
    actions_table.add_column("Command", style="bold cyan", width=3)
    actions_table.add_column("Action", style="white", width=25)
    actions_table.add_column("Description", style="dim")

    actions_table.add_row("q", "Quit", "Exit the CLI interface")
    actions_table.add_row("h", "Help", "Show detailed help for each tool")
    actions_table.add_row("s", "System Status", "Show overall system status")

    console.print(
        Panel(
            actions_table,
            title="⚡ Quick Actions",
            border_style="green",
        )
    )


def show_system_status():
    """Show overall system status"""
    try:
        # Get the backend directory (parent of cli)
        backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

        # Check FAQ database
        faq_db_path = os.path.join(backend_dir, "faqs.db")
        faq_status = "✅ Available" if os.path.exists(faq_db_path) else "❌ Missing"

        # Check cache status
        cache_metadata_path = os.path.join(backend_dir, "rag_cache", "metadata.json")
        cache_status = (
            "✅ Available" if os.path.exists(cache_metadata_path) else "❌ Not built"
        )

        # Check if API is running (simple check)
        api_status = "❓ Unknown"
        try:
            import requests

            response = requests.get("http://localhost:8000/health", timeout=2)
            api_status = "✅ Running" if response.status_code == 200 else "❌ Error"
        except:
            api_status = "❌ Not running"

        # Create status table
        status_table = Table(show_header=False, box=None, padding=(0, 2))
        status_table.add_column("Component", style="bold cyan", width=20)
        status_table.add_column("Status", style="white")

        status_table.add_row("📊 FAQ Database", faq_status)
        status_table.add_row("🔄 Vector Cache", cache_status)
        status_table.add_row("🌐 API Server", api_status)

        console.print(
            Panel(
                status_table,
                title="🔍 System Status",
                border_style="blue",
            )
        )

    except Exception as e:
        console.print(f"[red]❌ Failed to get system status: {e}[/red]")


def show_detailed_help():
    """Show detailed help for all tools"""
    help_text = """
[bold blue]Susten FAQ Bot CLI Tools - Detailed Help[/bold blue]

[bold green]1. FAQ Management (manage_faqs.py)[/bold green]
Comprehensive FAQ database management with rich CLI interface.

Commands:
• [cyan]list[/cyan] [limit] [--status public|private] [--category <category>] [--tag <tag>]
• [cyan]search[/cyan] <query> - Full-text search across FAQs
• [cyan]add[/cyan] '<question>' '<answer>' [--status] [--category] [--tags]
• [cyan]update[/cyan] <id> [--question] [--answer] [--status] [--category] [--tags]
• [cyan]delete[/cyan] <id> - Delete FAQ with confirmation
• [cyan]stats[/cyan] - Show comprehensive database statistics
• [cyan]tags[/cyan] - List all unique tags with counts
• [cyan]categories[/cyan] - List all categories with counts
• [cyan]sync[/cyan] <csv_file> - Sync data from CSV file

[bold green]2. Cache Management (manage_cache.py)[/bold green]
Vector cache management for optimal performance.

Commands:
• [cyan]status[/cyan] - Show cache status and file information
• [cyan]build[/cyan] [--force] [--include-private] - Build/rebuild cache
• [cyan]clear[/cyan] - Clear cache files with confirmation
• [cyan]test[/cyan] - Test cache functionality with sample query

[bold green]3. Interactive Query (query.py)[/bold green]
Interactive Q&A interface with the FAQ bot.

Features:
• Real-time question answering using vector search
• Context display showing source FAQs
• Session history and conversation management
• Rich formatting with syntax highlighting
• Use 'exit', 'quit', or 'q' to end session

[bold yellow]Usage Examples:[/bold yellow]
• [cyan]uv run python cli/manage_faqs.py list 10 --status public[/cyan]
• [cyan]uv run python cli/manage_cache.py build --include-private[/cyan]
• [cyan]uv run python cli/query.py[/cyan] (interactive mode - use exit/quit/q to end)

[bold yellow]System Requirements:[/bold yellow]
• FAQ database (faqs.db) must exist
• For cache operations: sufficient disk space and memory
• For query interface: API server should be running
    """

    console.print(Panel(help_text, title="📚 Detailed Help", border_style="cyan"))


def run_tool(command, args=None):
    """Run a CLI tool with optional arguments"""
    try:
        # Get the directory where this script is located
        script_dir = os.path.dirname(os.path.abspath(__file__))
        tool_path = os.path.join(script_dir, command)

        cmd = ["python", tool_path]
        if args:
            cmd.extend(args)

        # Run the command
        result = subprocess.run(cmd, capture_output=False)
        return result.returncode == 0

    except Exception as e:
        console.print(f"[red]❌ Failed to run {command}: {e}[/red]")
        return False


def tool_loop(tool):
    """Run a continuous loop for a specific tool until user wants to exit"""
    console.print(f"[bold green]📋 {tool['name']} - Interactive Mode[/bold green]")
    console.print("[dim]Type 'exit', 'quit', or 'q' to return to main menu[/dim]")
    console.print()

    while True:
        # Ask for command arguments
        args_input = Prompt.ask(
            f"[yellow]{tool['name']}[/yellow] [cyan]>[/cyan] Enter command (or 'help' for options)",
            default="",
        )

        # Handle exit conditions
        if args_input.lower() in ["exit", "quit", "q"]:
            console.print(f"[green]👋 Exiting {tool['name']}...[/green]")
            console.print()
            break

        # Default to help if no input
        args = args_input.split() if args_input.strip() else ["help"]

        console.print()
        console.print(
            f"[cyan]Running: python cli/{tool['command']} {' '.join(args)}[/cyan]"
        )
        console.print("=" * 80)

        # Run the tool
        success = run_tool(tool["command"], args)

        console.print("=" * 80)
        if success:
            console.print(f"[green]✅ Command completed successfully[/green]")
        else:
            console.print(f"[red]❌ Command encountered an error[/red]")

        console.print()


def interactive_mode():
    """Run the interactive CLI mode"""
    console.print()
    console.print(
        "[bold green]🌟 Welcome to Susten FAQ Bot CLI Management Interface[/bold green]"
    )
    console.print()

    while True:
        # Show main menu
        tools = show_main_menu()
        console.print()

        # Show quick actions
        show_quick_actions()
        console.print()

        # Get user choice
        choice = Prompt.ask(
            "[bold]Select a tool (1-3) or action (q/h/s)[/bold]",
            choices=["1", "2", "3", "q", "h", "s"],
            default="q",
        )

        console.print()

        if choice == "q":
            console.print("[green]👋 Goodbye![/green]")
            break

        elif choice == "h":
            show_detailed_help()
            console.print()
            Prompt.ask("[dim]Press Enter to continue[/dim]", default="")
            console.print()

        elif choice == "s":
            show_system_status()
            console.print()
            Prompt.ask("[dim]Press Enter to continue[/dim]", default="")
            console.print()

        elif choice in ["1", "2", "3"]:
            tool = tools[int(choice) - 1]
            console.print(f"[blue]🚀 Launching {tool['name']}...[/blue]")
            console.print()

            # Handle query tool differently - it's purely interactive
            if choice == "3":  # Interactive Query
                console.print(f"[cyan]Running: python cli/{tool['command']}[/cyan]")
                console.print("=" * 80)

                # Run query.py directly without arguments
                success = run_tool(tool["command"])

                console.print("=" * 80)
                if success:
                    console.print(
                        f"[green]✅ {tool['name']} completed successfully[/green]"
                    )
                else:
                    console.print(f"[red]❌ {tool['name']} encountered an error[/red]")

                console.print()
                Prompt.ask("[dim]Press Enter to return to main menu[/dim]", default="")
                console.print()
            else:
                # Enter tool-specific loop for FAQ and Cache management
                tool_loop(tool)


def direct_mode():
    """Handle direct command execution"""
    if len(sys.argv) < 2:
        console.print("[red]❌ No command specified[/red]")
        console.print(
            "[dim]Use --interactive for interactive mode or --help for help[/dim]"
        )
        return

    command = sys.argv[1]
    args = sys.argv[2:] if len(sys.argv) > 2 else []

    # Map command shortcuts to full commands
    command_map = {
        "faq": "manage_faqs.py",
        "faqs": "manage_faqs.py",
        "cache": "manage_cache.py",
        "query": "query.py",
        "ask": "query.py",
    }

    if command in command_map:
        tool_command = command_map[command]
        console.print(
            f"[blue]🚀 Running: python cli/{tool_command} {' '.join(args)}[/blue]"
        )
        console.print()
        run_tool(tool_command, args)
    else:
        console.print(f"[red]❌ Unknown command: {command}[/red]")
        console.print("[dim]Available commands: faq, cache, query[/dim]")


def main():
    """Main entry point"""
    # Show header
    header = Text("Susten FAQ Bot - CLI Management Interface", style="bold magenta")
    console.print(Align.center(header))
    console.print()

    # Check command line arguments
    if len(sys.argv) == 1 or "--interactive" in sys.argv:
        interactive_mode()
    elif "--help" in sys.argv or "-h" in sys.argv:
        show_detailed_help()
    else:
        direct_mode()


if __name__ == "__main__":
    main()
