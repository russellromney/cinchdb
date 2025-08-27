#!/usr/bin/env python3
"""Update version references in documentation files."""

import re
import sys
from pathlib import Path
import tomllib
import requests
from typing import Optional, Dict, List


def get_local_version() -> str:
    """Get version from pyproject.toml."""
    pyproject_path = Path(__file__).parent.parent / "pyproject.toml"
    with open(pyproject_path, "rb") as f:
        data = tomllib.load(f)
    return data["project"]["version"]


def get_pypi_version() -> Optional[str]:
    """Get the latest version from PyPI."""
    try:
        response = requests.get("https://pypi.org/pypi/cinchdb/json", timeout=10)
        if response.status_code == 200:
            data = response.json()
            return data["info"]["version"]
    except Exception as e:
        print(f"Warning: Could not fetch PyPI version: {e}")
    return None


def find_version_references(docs_dir: Path) -> Dict[Path, List[str]]:
    """Find files that might contain version references."""
    version_files = {}
    
    # Common patterns that might indicate version references
    patterns = [
        r'\b\d+\.\d+\.\d+\b',  # Semantic version pattern
        r'cinchdb==\d+\.\d+\.\d+',  # pip install with version
        r'version.*\d+\.\d+',  # version mentions
        r'pypi.*cinchdb',  # PyPI references
    ]
    
    for doc_file in docs_dir.rglob("*.md"):
        try:
            content = doc_file.read_text(encoding="utf-8")
            matches = []
            
            for pattern in patterns:
                found = re.findall(pattern, content, re.IGNORECASE)
                matches.extend(found)
            
            if matches:
                version_files[doc_file] = matches
                
        except Exception as e:
            print(f"Warning: Could not read {doc_file}: {e}")
    
    return version_files


def update_installation_docs(docs_dir: Path, current_version: str, pypi_version: Optional[str]):
    """Update installation documentation with current version info."""
    installation_file = docs_dir / "getting-started" / "installation.md"
    
    if not installation_file.exists():
        print(f"Installation file not found: {installation_file}")
        return
    
    try:
        content = installation_file.read_text(encoding="utf-8")
        
        # Add version information section if it doesn't exist
        version_section = f"""

## Current Version

- **Latest Release**: {current_version}"""
        
        if pypi_version and pypi_version != current_version:
            version_section += f"""
- **PyPI**: {pypi_version}
- **Note**: Local version ({current_version}) is newer than PyPI ({pypi_version})"""
        elif pypi_version:
            version_section += f"""
- **PyPI**: {pypi_version} ✅"""
        
        version_section += f"""

You can check the installed version with:
```bash
cinch version
# or
python -c "import cinchdb; print(cinchdb.__version__)"
```
"""
        
        # Insert version section after "Verify Installation" section
        verify_pattern = r'(## Verify Installation.*?```bash\ncinch version\n```)'
        if re.search(verify_pattern, content, re.DOTALL):
            # Replace existing verification section with enhanced version
            new_verify_section = f"""## Verify Installation

Check that CinchDB is installed correctly:

```bash
cinch version
```

Expected output: `CinchDB version {current_version}`{version_section}"""
            
            content = re.sub(verify_pattern, new_verify_section, content, flags=re.DOTALL)
        else:
            # Append version section if no verify section exists
            content += version_section
        
        # Update file
        installation_file.write_text(content, encoding="utf-8")
        print(f"✅ Updated {installation_file}")
        
    except Exception as e:
        print(f"Error updating {installation_file}: {e}")


def add_version_badge_to_readme(readme_path: Path, current_version: str):
    """Add a PyPI version badge to README if it doesn't exist."""
    try:
        content = readme_path.read_text(encoding="utf-8")
        
        # Check if badge already exists
        if "shields.io" in content or "pypi.org/project/cinchdb" in content:
            print("Version badge already exists in README")
            return
        
        # Add badges after the title
        badge_section = f"""
[![PyPI version](https://badge.fury.io/py/cinchdb.svg)](https://badge.fury.io/py/cinchdb)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

"""
        
        # Insert after the main title and description
        title_pattern = r'(# CinchDB\n\n\*\*[^*]+\*\*\n)'
        if re.search(title_pattern, content):
            content = re.sub(title_pattern, r'\1' + badge_section, content)
            readme_path.write_text(content, encoding="utf-8")
            print(f"✅ Added version badge to {readme_path}")
        else:
            print("Could not find appropriate place to insert badge in README")
            
    except Exception as e:
        print(f"Error updating README: {e}")


def main():
    """Main function to update documentation versions."""
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    docs_dir = project_root / "docs"
    readme_path = project_root / "README.md"
    
    print("🔍 Checking CinchDB version information...")
    
    # Get versions
    local_version = get_local_version()
    print(f"Local version: {local_version}")
    
    pypi_version = get_pypi_version()
    if pypi_version:
        print(f"PyPI version: {pypi_version}")
    else:
        print("Could not retrieve PyPI version")
    
    # Update documentation
    print("\n📝 Updating documentation...")
    
    if docs_dir.exists():
        # Find existing version references
        version_refs = find_version_references(docs_dir)
        if version_refs:
            print("\nFound potential version references:")
            for file_path, matches in version_refs.items():
                rel_path = file_path.relative_to(project_root)
                print(f"  {rel_path}: {matches}")
        
        # Update installation docs
        update_installation_docs(docs_dir, local_version, pypi_version)
    else:
        print(f"Docs directory not found: {docs_dir}")
    
    # Update README
    if readme_path.exists():
        add_version_badge_to_readme(readme_path, local_version)
    else:
        print(f"README not found: {readme_path}")
    
    print("\n✅ Documentation version update complete!")


if __name__ == "__main__":
    main()