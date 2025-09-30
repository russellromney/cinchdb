#!/usr/bin/env python3
"""Script to fix all test fixtures to use ConnectionContext."""

import re
from pathlib import Path

# Pattern to match manager instantiations in tests
MANAGER_PATTERN = re.compile(
    r'(\w+Manager)\((temp_project|project_dir|project_root|self\.project_root),\s*"(\w+)",\s*"(\w+)"(?:,\s*"(\w+)")?(?:,\s*(\w+))?\)',
    re.MULTILINE
)

def fix_file(file_path: Path):
    """Fix a single test file."""
    content = file_path.read_text()
    original = content

    # Check if already has ConnectionContext import
    has_context_import = 'from cinchdb.managers.base import ConnectionContext' in content

    # Find all manager instantiations
    matches = list(MANAGER_PATTERN.finditer(content))

    if not matches:
        return False

    print(f"\n{file_path.name}: Found {len(matches)} manager instantiations")

    # Add import if needed
    if not has_context_import:
        # Find where to add import (after other cinchdb imports)
        import_pos = content.find('from cinchdb.')
        if import_pos != -1:
            # Find end of that line
            line_end = content.find('\n', import_pos)
            content = (
                content[:line_end + 1] +
                'from cinchdb.managers.base import ConnectionContext\n' +
                content[line_end + 1:]
            )

    # Replace all manager instantiations from last to first (to preserve positions)
    for match in reversed(matches):
        manager_name = match.group(1)
        project_var = match.group(2)
        db_name = match.group(3)
        branch_name = match.group(4)
        tenant_name = match.group(5) if match.group(5) else "main"
        encryption = match.group(6)

        # Build context creation
        context_parts = [
            f"project_root={project_var}",
            f'database="{db_name}"',
            f'branch="{branch_name}"',
        ]

        if tenant_name != "main":
            context_parts.append(f'tenant="{tenant_name}"')

        if encryption:
            context_parts.append(f"encryption_manager={encryption}")

        replacement = f"{manager_name}(ConnectionContext({', '.join(context_parts)}))"

        content = content[:match.start()] + replacement + content[match.end():]

    if content != original:
        file_path.write_text(content)
        print(f"  ✓ Fixed {file_path.name}")
        return True

    return False

def main():
    tests_dir = Path(__file__).parent.parent / 'tests'

    if not tests_dir.exists():
        print(f"Error: {tests_dir} not found")
        return

    fixed_count = 0

    # Fix all test files recursively
    for py_file in tests_dir.rglob('test_*.py'):
        if fix_file(py_file):
            fixed_count += 1

    print(f"\n✓ Fixed {fixed_count} test files")

if __name__ == '__main__':
    main()
