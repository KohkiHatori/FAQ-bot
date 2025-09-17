#!/bin/bash
#
# Setup Git Hooks Script
# This script recreates the git pre-commit hooks for the Susten FAQ Bot project
# Run this after cloning the repository to enable automatic code formatting
#

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if we're in a git repository
if [ ! -d ".git" ]; then
    print_error "This script must be run from the root of a git repository"
    exit 1
fi

print_status "Setting up git hooks for Susten FAQ Bot..."

# Check if uv is installed
if ! command -v uv >/dev/null 2>&1; then
    print_error "uv is not installed or not in PATH"
    print_status "Please install uv first: https://docs.astral.sh/uv/"
    exit 1
fi

print_success "uv is available"

# Check if black is available via uv
if ! uv run black --version >/dev/null 2>&1; then
    print_error "Black is not available via uv"
    print_status "Please run 'uv sync' to install dependencies first"
    exit 1
fi

print_success "Black formatter is available"

# Create the pre-commit hook
HOOK_FILE=".git/hooks/pre-commit"

print_status "Creating pre-commit hook at $HOOK_FILE"

cat > "$HOOK_FILE" << 'EOF'
#!/bin/sh
#
# Pre-commit hook to automatically format Python files with black
#

# Check if black is available
if ! command -v uv >/dev/null 2>&1; then
    echo "Error: uv is not installed or not in PATH"
    exit 1
fi

# Get list of Python files that are staged for commit
PYTHON_FILES=$(git diff --cached --name-only --diff-filter=ACM | grep '\.py$')

if [ -z "$PYTHON_FILES" ]; then
    # No Python files to format
    exit 0
fi

echo "Running black formatter on staged Python files..."

# Format the files
for file in $PYTHON_FILES; do
    if [ -f "$file" ]; then
        echo "Formatting: $file"
        uv run black "$file"
        # Re-stage the file after formatting
        git add "$file"
    fi
done

echo "Black formatting completed."
exit 0
EOF

# Make the hook executable
chmod +x "$HOOK_FILE"

print_success "Pre-commit hook created and made executable"

# Test the hook
print_status "Testing the pre-commit hook..."

if [ -x "$HOOK_FILE" ]; then
    print_success "Pre-commit hook is executable"
else
    print_error "Pre-commit hook is not executable"
    exit 1
fi

# Show hook status
print_status "Git hooks setup completed!"
echo
echo "📋 What this hook does:"
echo "  • Automatically formats Python files with Black before each commit"
echo "  • Only processes staged Python files (.py)"
echo "  • Re-stages formatted files automatically"
echo
echo "🔧 Usage:"
echo "  • Just commit as usual: git commit -m 'Your message'"
echo "  • The hook will run automatically and format your Python code"
echo "  • To bypass the hook (not recommended): git commit --no-verify"
echo
echo "⚙️  Configuration:"
echo "  • Black settings are configured in pyproject.toml"
echo "  • Line length: 88 characters"
echo "  • Target Python version: 3.9+"
echo

print_success "🎉 Git hooks are now set up and ready to use!"