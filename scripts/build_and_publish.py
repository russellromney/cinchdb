#!/usr/bin/env python3
"""Build and publish CinchDB Python package to PyPI using uv."""

import os
import sys
import subprocess
import shutil
from pathlib import Path
import tempfile
import argparse


def run_command(
    cmd: list[str], check: bool = True, **kwargs
) -> subprocess.CompletedProcess:
    """Run a command and return the result."""
    print(f"Running: {' '.join(cmd)}")
    return subprocess.run(cmd, check=check, **kwargs)


def clean_build_artifacts():
    """Remove existing build artifacts."""
    print("Cleaning build artifacts...")
    artifacts = ["dist", "build", "*.egg-info", "src/*.egg-info"]
    for pattern in artifacts:
        for path in Path(".").glob(pattern):
            if path.is_dir():
                shutil.rmtree(path)
                print(f"  Removed directory: {path}")
            else:
                path.unlink()
                print(f"  Removed file: {path}")


def create_source_distribution():
    """Create a source distribution with only Python package files."""
    print("\nCreating source distribution...")

    # Create a temporary directory for the clean build
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        project_name = "cinchdb"
        temp_project = temp_path / project_name

        # Copy only the necessary files
        print("Copying Python package files...")

        # Essential files at root
        files_to_copy = [
            "pyproject.toml",
            "README.md",
            "LICENSE",
        ]

        for file in files_to_copy:
            if Path(file).exists():
                shutil.copy2(file, temp_project / file)
                print(f"  Copied: {file}")

        # Copy the src directory (Python package)
        src_dir = Path("src")
        if src_dir.exists():
            shutil.copytree(
                src_dir,
                temp_project / "src",
                ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store"),
            )
            print(f"  Copied: src/")

        # Create a minimal .gitignore to exclude unwanted files
        gitignore_content = """
# Build artifacts
dist/
build/
*.egg-info/
__pycache__/
*.pyc
.DS_Store

# Other non-Python directories
docs/
sdk/
site/
examples/
scripts/
tests/
.github/
.vscode/

# Development files
.env
.venv/
venv/
*.log
.coverage
.pytest_cache/
.mypy_cache/
.ruff_cache/
"""
        (temp_project / ".gitignore").write_text(gitignore_content.strip())

        # Build using uv in the temporary directory
        original_dir = os.getcwd()
        try:
            os.chdir(temp_project)

            # Use uv to build the package
            run_command(["uv", "build"])

            # Copy the built distributions back to the original directory
            temp_dist = temp_project / "dist"
            if temp_dist.exists():
                # Create dist directory in original location if it doesn't exist
                original_dist = Path(original_dir) / "dist"
                original_dist.mkdir(exist_ok=True)

                # Copy all built files
                for file in temp_dist.iterdir():
                    shutil.copy2(file, original_dist)
                    print(f"  Built: {file.name}")

        finally:
            os.chdir(original_dir)


def check_package_contents():
    """Verify the built package contains only Python files."""
    print("\nChecking package contents...")

    dist_dir = Path("dist")
    if not dist_dir.exists():
        print("ERROR: dist directory not found!")
        return False

    # Find the wheel file
    wheel_files = list(dist_dir.glob("*.whl"))
    if not wheel_files:
        print("ERROR: No wheel file found!")
        return False

    wheel_file = wheel_files[0]
    print(f"Inspecting wheel: {wheel_file.name}")

    # List contents of the wheel file
    import zipfile

    with zipfile.ZipFile(wheel_file, "r") as zf:
        files = zf.namelist()

        # Check for unwanted directories
        unwanted_patterns = ["docs/", "sdk/", "site/", "examples/typescript"]
        found_unwanted = False

        for file in files:
            for pattern in unwanted_patterns:
                if pattern in file:
                    print(f"  WARNING: Found unwanted file: {file}")
                    found_unwanted = True

        if found_unwanted:
            print("WARNING: Package contains unwanted files!")
            return False

        # Show summary of what's included
        print(f"  Total files: {len(files)}")
        print("  Package contents look good!")

        # Show first few files as sample
        print("  Sample files:")
        for file in sorted(files)[:10]:
            print(f"    - {file}")
        if len(files) > 10:
            print(f"    ... and {len(files) - 10} more files")

    return True


def publish_to_pypi(repository: str = "pypi", skip_existing: bool = False):
    """Publish the package to PyPI using uv."""
    print(f"\nPublishing to {repository}...")

    cmd = ["uv", "publish"]

    if repository == "testpypi":
        cmd.extend(["--publish-url", "https://test.pypi.org/legacy/"])

    if skip_existing:
        # uv doesn't have a direct skip-existing flag, but it will fail gracefully
        # if the package already exists
        pass

    # Note: uv will prompt for credentials if not configured
    # You can set UV_PUBLISH_USERNAME and UV_PUBLISH_PASSWORD environment variables
    # or use UV_PUBLISH_TOKEN for token authentication

    try:
        run_command(cmd)
        print(f"Successfully published to {repository}!")
    except subprocess.CalledProcessError as e:
        if "already exists" in str(e):
            print(f"Package version already exists on {repository}")
            if not skip_existing:
                return False
        else:
            print(f"Failed to publish: {e}")
            return False

    return True


def main():
    """Main build and publish workflow."""
    parser = argparse.ArgumentParser(description="Build and publish CinchDB to PyPI")
    parser.add_argument(
        "--publish", action="store_true", help="Publish to PyPI after building"
    )
    parser.add_argument(
        "--testpypi", action="store_true", help="Publish to TestPyPI instead of PyPI"
    )
    parser.add_argument(
        "--skip-existing", action="store_true", help="Skip if version already exists"
    )
    parser.add_argument(
        "--no-clean", action="store_true", help="Don't clean build artifacts first"
    )
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Only check package contents, don't build",
    )

    args = parser.parse_args()

    # Change to project root
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    os.chdir(project_root)
    print(f"Working directory: {os.getcwd()}")

    if args.check_only:
        # Just check existing package
        if check_package_contents():
            print("\nPackage check passed!")
            return 0
        else:
            print("\nPackage check failed!")
            return 1

    # Clean unless told not to
    if not args.no_clean:
        clean_build_artifacts()

    # Build the package
    try:
        create_source_distribution()
    except Exception as e:
        print(f"\nBuild failed: {e}")
        return 1

    # Verify package contents
    if not check_package_contents():
        print("\nWARNING: Package may contain unwanted files!")
        response = input("Continue anyway? (y/N): ")
        if response.lower() != "y":
            return 1

    # Publish if requested
    if args.publish or args.testpypi:
        repository = "testpypi" if args.testpypi else "pypi"

        print(f"\nReady to publish to {repository}")
        print("Package files:")
        for file in Path("dist").iterdir():
            print(f"  - {file.name} ({file.stat().st_size / 1024:.1f} KB)")

        if not args.testpypi:  # Extra confirmation for production PyPI
            response = input(f"\nPublish to {repository}? (y/N): ")
            if response.lower() != "y":
                print("Aborted.")
                return 0

        if not publish_to_pypi(repository, args.skip_existing):
            return 1

    print("\nBuild completed successfully!")
    print("\nNext steps:")
    if not (args.publish or args.testpypi):
        print("  - Review the built packages in the 'dist' directory")
        print(
            "  - To publish to TestPyPI: python scripts/build_and_publish.py --testpypi"
        )
        print("  - To publish to PyPI: python scripts/build_and_publish.py --publish")
    else:
        print(f"  - Package published to {repository}")
        print(
            "  - Install with: pip install cinchdb"
            + (" -i https://test.pypi.org/simple/" if args.testpypi else "")
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
