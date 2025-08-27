# Automated Documentation Version Updates

This document explains the automated system for keeping documentation synchronized with the current CinchDB version.

## Overview

The version update system automatically:
- 🔍 **Detects** the current version from `pyproject.toml`
- 📡 **Fetches** the latest PyPI version for comparison
- 📝 **Updates** documentation with current version information
- 🎨 **Adds** version badges to README if missing
- 🔄 **Runs** automatically in CI/CD and build processes

## Components

### 1. Version Update Script
**Location**: `scripts/update_docs_version.py`

**Features**:
- Reads local version from `pyproject.toml`
- Fetches current PyPI version via API
- Updates installation documentation with version info
- Adds PyPI version badges to README
- Shows comparison between local and PyPI versions

**Usage**:
```bash
# Manual run
python scripts/update_docs_version.py

# Via Makefile
make update-docs
```

### 2. Build Integration
**Location**: `scripts/build_and_publish.py`

The build script automatically runs documentation updates after building but before publishing:

```bash
# Build with automatic docs update
python scripts/build_and_publish.py --publish
```

### 3. GitHub Actions Integration

#### Test Workflow
**Location**: `.github/workflows/test.yml`

Automatically updates docs during CI/CD runs:
- Installs required dependencies (`requests`, `tomli`)
- Runs `make update-docs`
- Commits changes if documentation is modified (main branch only)

#### Dedicated Documentation Workflow  
**Location**: `.github/workflows/update-docs.yml`

Triggered by:
- Version changes in `pyproject.toml`
- Manual dispatch
- Completion of release workflows

### 4. Makefile Integration
**Location**: `Makefile`

Provides convenient local command:
```bash
make update-docs
```

## What Gets Updated

### Installation Documentation
**File**: `docs/getting-started/installation.md`

**Updates**:
- Expected output in "Verify Installation" section
- Current version information section
- PyPI version comparison
- Version checking commands

**Example Addition**:
```markdown
## Current Version

- **Latest Release**: 0.1.15
- **PyPI**: 0.1.15 ✅

You can check the installed version with:
\`\`\`bash
cinch version
# or
python -c "import cinchdb; print(cinchdb.__version__)"
\`\`\`
```

### README Badges
**File**: `README.md`

**Adds** (if missing):
```markdown
[![PyPI version](https://badge.fury.io/py/cinchdb.svg)](https://badge.fury.io/py/cinchdb)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
```

## Automation Triggers

### During Development
1. **Manual**: `make update-docs`
2. **Build Process**: Automatic during `build_and_publish.py`
3. **Version Bump**: CI detects `pyproject.toml` changes

### In CI/CD
1. **Every Test Run**: Updates docs and commits if changed (main branch)
2. **Version Changes**: Triggered by `pyproject.toml` modifications
3. **Post-Release**: After successful release workflows

## Version Comparison Logic

The script intelligently handles different scenarios:

### Local = PyPI
```
- **Latest Release**: 0.1.15
- **PyPI**: 0.1.15 ✅
```

### Local > PyPI (Development)
```
- **Latest Release**: 0.1.16
- **PyPI**: 0.1.15
- **Note**: Local version (0.1.16) is newer than PyPI (0.1.15)
```

### PyPI Unavailable
```
- **Latest Release**: 0.1.15
- **PyPI**: Unable to fetch
```

## Dependencies

The update script requires:
- `requests` - For PyPI API calls
- `tomllib` - For reading `pyproject.toml` (Python 3.11+)

These are automatically installed by the build process and CI/CD workflows.

## Error Handling

The system is designed to be robust:
- **API failures**: Gracefully handles PyPI API unavailability
- **File errors**: Continues if documentation files are missing
- **Build integration**: Never fails the build if docs update fails

## Customization

To modify what gets updated:

1. **Edit the script**: `scripts/update_docs_version.py`
2. **Modify patterns**: Update `find_version_references()` function
3. **Change templates**: Modify version section templates in `update_installation_docs()`
4. **Add new files**: Extend the script to handle additional documentation files

## Testing

Test the system locally:

```bash
# Test the update script
cd cinchdb
make update-docs

# Check what changed
git diff docs/ README.md

# Test build integration
python scripts/build_and_publish.py --check-only
```

## Benefits

✅ **Consistency**: Documentation always reflects the current version  
✅ **Automation**: No manual work required  
✅ **CI Integration**: Updates happen automatically during development  
✅ **PyPI Sync**: Shows relationship between local and published versions  
✅ **Error Recovery**: Robust error handling prevents build failures  
✅ **Developer Friendly**: Simple `make update-docs` command  

This system ensures users always see current, accurate version information without manual maintenance overhead.