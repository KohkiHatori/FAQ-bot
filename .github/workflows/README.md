# GitHub Actions Workflows

## Python CI (`python-ci.yml`)

This workflow runs on every push and pull request to the `main` and `develop` branches.

### What it does:

1. **Black Formatting Check**: Verifies that all Python files in the `backend/` directory follow Black code formatting standards
   - Uses `black --check --diff` to show formatting differences without making changes
   - Fails the CI if any files are not properly formatted

2. **Pytest Execution**: Runs the complete test suite
   - Executes all tests with coverage reporting
   - Uses `pytest` with coverage options
   - Suppresses external library warnings for clean output

3. **Coverage Reporting**: Uploads HTML coverage reports as artifacts
   - Available for download from the GitHub Actions interface
   - Retained for 30 days

### Environment:
- **Python**: 3.11
- **Package Manager**: uv
- **OS**: Ubuntu Latest
- **Dependencies**: Automatically installs dev dependencies and test requirements

### Key Features:
- ✅ **Fast execution** using uv package manager
- ✅ **Clean output** with warning suppression
- ✅ **Comprehensive testing** with coverage reporting
- ✅ **Code quality** enforcement through Black formatting

### Usage:
The workflow runs automatically on:
- Push to `main` or `develop` branches
- Pull requests targeting `main` or `develop` branches

### Status:
- ✅ **Black formatting check** - Ensures consistent code style
- ✅ **All tests pass** - Validates functionality and prevents regressions
- 📊 **Coverage reporting** - Tracks test coverage metrics 