#!/usr/bin/env python3
"""Script to fix all CLI command files to use ConnectionContext."""

import re
from pathlib import Path

# Pattern to match manager instantiations
MANAGER_PATTERN = re.compile(
    r'(\w+Manager)\((config\.project_dir|project_dir),\s*([^,]+),\s*([^,\)]+)(?:,\s*([^,\)]+))?(?:,\s*([^,\)]+))?\)',
    re.MULTILINE
)

def fix_file(file_path: Path):
    """Fix a single CLI command file."""
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
        db_name = match.group(3).strip()
        branch_name = match.group(4).strip() if match.group(4) else None
        tenant_name = match.group(5).strip() if match.group(5) else None
        extra = match.group(6)

        # Build context creation
        context_parts = [
            f"project_root={project_var}",
            f"database={db_name}",
        ]

        if branch_name:
            context_parts.append(f"branch={branch_name}")

        if tenant_name and tenant_name not in ['"main"', "'main'"]:
            context_parts.append(f"tenant={tenant_name}")

        if extra:
            context_parts.append(f"encryption_manager={extra}")

        replacement = f"{manager_name}(ConnectionContext({', '.join(context_parts)}))"

        content = content[:match.start()] + replacement + content[match.end():]

    if content != original:
        file_path.write_text(content)
        print(f"  ✓ Fixed {file_path.name}")
        return True

    return False

def main():
    cli_commands_dir = Path(__file__).parent.parent / 'src' / 'cinchdb' / 'cli' / 'commands'
    cli_handlers_dir = Path(__file__).parent.parent / 'src' / 'cinchdb' / 'cli' / 'handlers'

    if not cli_commands_dir.exists():
        print(f"Error: {cli_commands_dir} not found")
        return

    fixed_count = 0

    # Fix commands
    for py_file in cli_commands_dir.glob('*.py'):
        if py_file.name == '__init__.py':
            continue
        if fix_file(py_file):
            fixed_count += 1

    # Fix handlers
    if cli_handlers_dir.exists():
        for py_file in cli_handlers_dir.glob('*.py'):
            if py_file.name == '__init__.py':
                continue
            if fix_file(py_file):
                fixed_count += 1

    print(f"\n✓ Fixed {fixed_count} files")

if __name__ == '__main__':
    main()
