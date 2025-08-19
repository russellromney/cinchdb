# CinchDB Build and Publishing Guide

This guide explains how to build and publish the CinchDB Python package to PyPI.

## Prerequisites

- Python 3.10 or higher
- `uv` package manager installed (`pip install uv`)
- PyPI account and API token (for publishing)

## Building the Package

### Quick Build

Use the simple shell script for a quick build:

```bash
./scripts/build.sh
```

This will:
- Clean previous build artifacts
- Build the package using `uv`
- Show the built files and their sizes

### Advanced Build

Use the Python script for more control:

```bash
# Basic build
python scripts/build_and_publish.py

# Check package contents without building
python scripts/build_and_publish.py --check-only

# Build without cleaning artifacts
python scripts/build_and_publish.py --no-clean
```

## Publishing to PyPI

### Test Publishing (TestPyPI)

First, test your package on TestPyPI:

```bash
# Using the build script
python scripts/build_and_publish.py --testpypi

# Or using uv directly
uv publish --publish-url https://test.pypi.org/legacy/
```

### Production Publishing (PyPI)

Once tested, publish to production PyPI:

```bash
# Using the build script (with confirmation prompt)
python scripts/build_and_publish.py --publish

# Or using uv directly
uv publish
```

### Authentication

Set up authentication using one of these methods:

1. **Environment Variables** (Recommended for CI/CD):
   ```bash
   export UV_PUBLISH_TOKEN="your-pypi-api-token"
   # Or for username/password (not recommended)
   export UV_PUBLISH_USERNAME="__token__"
   export UV_PUBLISH_PASSWORD="your-pypi-api-token"
   ```

2. **Interactive** (uv will prompt for credentials)

## GitHub Actions

The repository includes a GitHub Actions workflow for automated publishing:

- **On Release**: Automatically publishes to PyPI when a release is created
- **Manual Trigger**: Can manually publish to TestPyPI or PyPI

Required secrets:
- `PYPI_API_TOKEN`: Your PyPI API token
- `TEST_PYPI_API_TOKEN`: Your TestPyPI API token

## What's Included

The build process includes only the Python package:
- `src/cinchdb/` - Core Python package with API and CLI
- `README.md` - Package documentation
- `LICENSE` - License file
- `pyproject.toml` - Package metadata

The following are explicitly excluded:
- `docs/` - Documentation site source
- `sdk/` - TypeScript SDK
- `examples/` - Example code
- `tests/` - Test files
- Scripts and development files

## Troubleshooting

### Package Contains Unwanted Files

If the package check shows unwanted files:

1. Check `pyproject.toml` for the `[tool.hatch.build]` configuration
2. Ensure exclude patterns are correct
3. Clean build artifacts and rebuild: `./scripts/build.sh`

### Authentication Errors

If you get authentication errors:

1. Ensure your PyPI API token is valid
2. Use `__token__` as username when using API tokens
3. Check token permissions (need upload permissions)

### Version Already Exists

If the version already exists on PyPI:

1. Bump the version in `pyproject.toml`
2. Rebuild the package
3. Or use `--skip-existing` flag to ignore the error

## Version Management

Update the version in `pyproject.toml`:

```toml
[project]
name = "cinchdb"
version = "0.1.1"  # Increment this
```

Follow semantic versioning:
- MAJOR.MINOR.PATCH (e.g., 1.2.3)
- MAJOR: Breaking changes
- MINOR: New features (backwards compatible)
- PATCH: Bug fixes