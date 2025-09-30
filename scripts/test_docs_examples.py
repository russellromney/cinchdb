#!/usr/bin/env python3
"""
Extract and validate Python code examples from documentation.

This script:
1. Finds all Python code blocks in markdown docs
2. Checks for syntax errors
3. Validates API signatures match actual code
4. Reports any issues
"""

import ast
import re
import sys
from pathlib import Path
from typing import List, Tuple


def extract_python_blocks(md_file: Path) -> List[Tuple[int, str]]:
    """Extract Python code blocks from markdown file with line numbers."""
    content = md_file.read_text()
    blocks = []

    # Find all ```python ... ``` blocks
    pattern = r'```python\n(.*?)```'
    for match in re.finditer(pattern, content, re.DOTALL):
        code = match.group(1)
        # Find line number where this block starts
        start_pos = match.start()
        line_num = content[:start_pos].count('\n') + 1
        blocks.append((line_num, code))

    return blocks


def is_pseudo_code(code: str) -> bool:
    """Check if code block is pseudo-code/illustrative (not meant to run)."""
    # Skip blocks with ellipsis placeholder
    if '...' in code and not code.strip().startswith('#'):
        return True
    # Skip blocks with type hints only (signature examples)
    if '->' in code and 'def ' not in code and 'return' not in code:
        return True
    # Skip parameter documentation
    if code.strip().startswith('Args:') or code.strip().startswith('Returns:'):
        return True
    return False


def check_syntax(code: str) -> Tuple[bool, str]:
    """Check if Python code has valid syntax."""
    # Skip pseudo-code/illustrative examples
    if is_pseudo_code(code):
        return True, "skipped (pseudo-code)"

    try:
        ast.parse(code)
        return True, ""
    except SyntaxError as e:
        return False, f"Syntax error at line {e.lineno}: {e.msg}"


def check_api_patterns(code: str) -> List[str]:
    """Check for known incorrect API patterns."""
    issues = []

    # Check for old update() signature: db.update("table", id, {...})
    # Should be: db.update("table", {"id": id, ...})
    old_update_pattern = r'db\.update\(["\'][\w_]+["\']\s*,\s*[\w\[\]"\'\.]+\s*,\s*\{[^}]*\}'
    if re.search(old_update_pattern, code):
        issues.append("Found old db.update() signature - should be db.update(table, {'id': id, ...})")

    # Check for old create_index() signature: db.create_index(name, table, cols)
    # Should be: db.create_index(table, cols, name=name)
    old_index_pattern = r'db\.create_index\(["\'][\w_]+["\']\s*,\s*["\'][\w_]+["\']\s*,\s*\['
    if re.search(old_index_pattern, code):
        issues.append("Found old db.create_index() signature - should be db.create_index(table, cols, name=...)")

    return issues


def main():
    docs_dir = Path(__file__).parent.parent / "docs"

    if not docs_dir.exists():
        print(f"Error: docs directory not found at {docs_dir}")
        sys.exit(1)

    print("=" * 70)
    print("Documentation Code Examples Validator")
    print("=" * 70)
    print()

    total_blocks = 0
    total_files = 0
    syntax_errors = 0
    api_issues = 0

    # Find all markdown files
    md_files = sorted(docs_dir.rglob("*.md"))

    for md_file in md_files:
        rel_path = md_file.relative_to(docs_dir)
        blocks = extract_python_blocks(md_file)

        if not blocks:
            continue

        total_files += 1
        file_has_issues = False

        for line_num, code in blocks:
            total_blocks += 1

            # Check syntax
            valid, error = check_syntax(code)
            if not valid:
                if not file_has_issues:
                    print(f"\n📄 {rel_path}")
                    file_has_issues = True
                print(f"  ❌ Line {line_num}: {error}")
                syntax_errors += 1
                continue

            # Check API patterns
            issues = check_api_patterns(code)
            if issues:
                if not file_has_issues:
                    print(f"\n📄 {rel_path}")
                    file_has_issues = True
                for issue in issues:
                    print(f"  ⚠️  Line {line_num}: {issue}")
                api_issues += 1

    # Summary
    print()
    print("=" * 70)
    print("Summary")
    print("=" * 70)
    print(f"Files with Python code: {total_files}")
    print(f"Total code blocks: {total_blocks}")
    print(f"Syntax errors: {syntax_errors}")
    print(f"API pattern issues: {api_issues}")
    print()

    if syntax_errors > 0 or api_issues > 0:
        print("❌ Found issues in documentation")
        sys.exit(1)
    else:
        print("✅ All code examples are valid!")
        sys.exit(0)


if __name__ == "__main__":
    main()
