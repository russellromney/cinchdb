#!/bin/bash
# Simple build script for CinchDB Python package

set -e  # Exit on error

echo "Building CinchDB Python package..."

# Change to project root
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR/.."

# Clean previous builds
echo "Cleaning previous builds..."
rm -rf dist/ build/ *.egg-info src/*.egg-info

# Build the package using uv
echo "Building package with uv..."
uv build

# Check the built files
echo -e "\nBuilt packages:"
ls -la dist/

# Show package size
echo -e "\nPackage sizes:"
du -h dist/*

echo -e "\nBuild complete!"
echo "To publish to TestPyPI: uv publish --publish-url https://test.pypi.org/legacy/"
echo "To publish to PyPI: uv publish"