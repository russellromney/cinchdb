#!/usr/bin/env python3
"""
Run actual Python code examples from documentation to verify they work.

This script extracts Python code blocks and executes them in a real environment
to ensure documentation examples are accurate and functional.
"""

import re
import sys
import tempfile
import traceback
from pathlib import Path
from typing import List, Tuple


def extract_runnable_blocks(md_file: Path) -> List[Tuple[int, str]]:
    """Extract runnable Python code blocks (skip pseudo-code)."""
    content = md_file.read_text()
    blocks = []

    pattern = r'```python\n(.*?)```'
    for match in re.finditer(pattern, content, re.DOTALL):
        code = match.group(1)
        start_pos = match.start()
        line_num = content[:start_pos].count('\n') + 1

        # Skip pseudo-code
        if '...' in code and not code.strip().startswith('#'):
            continue
        if 'Args:' in code or 'Returns:' in code:
            continue
        # Skip comment-only blocks
        if all(line.strip().startswith('#') or not line.strip() for line in code.split('\n')):
            continue

        blocks.append((line_num, code))

    return blocks


def create_test_setup() -> str:
    """Create setup code for isolated test environment."""
    return '''
import tempfile
import os
import sys
from pathlib import Path

# Create isolated test environment
test_dir = tempfile.mkdtemp(prefix="cinchdb_doctest_")
os.chdir(test_dir)

# Import cinchdb
import cinchdb
from cinchdb.models import Column

# Initialize test project
os.makedirs(".cinchdb", exist_ok=True)

# Helper to clean up test context
def cleanup():
    import shutil
    try:
        shutil.rmtree(test_dir)
    except:
        pass
'''


def run_code_block(code: str, setup: str = "") -> Tuple[bool, str]:
    """Execute a code block and return success status and output/error."""
    full_code = setup + "\n\n" + code

    # Create namespace for execution
    namespace = {}

    try:
        exec(full_code, namespace)
        return True, "OK"
    except Exception as e:
        error_msg = f"{type(e).__name__}: {str(e)}"
        # Include traceback for debugging
        tb = traceback.format_exc()
        return False, f"{error_msg}\n{tb}"


def is_example_that_should_fail(code: str) -> bool:
    """Check if this is an example demonstrating an error."""
    # Examples showing errors
    if "# Raises:" in code or "# Error:" in code:
        return True
    if "# ❌" in code or "# Dangerous" in code:
        return True
    if "# Common errors:" in code:
        return True
    return False


def main():
    docs_dir = Path(__file__).parent.parent / "docs"

    print("=" * 70)
    print("Documentation Code Examples Runner")
    print("=" * 70)
    print()
    print("⚠️  WARNING: This will actually execute code from docs!")
    print("    Make sure you're in a safe environment.")
    print()

    # Setup code
    setup = create_test_setup()

    total_blocks = 0
    passed = 0
    failed = 0
    skipped = 0

    # Focus on Python SDK docs (most important)
    md_files = sorted((docs_dir / "python-sdk").glob("*.md"))

    for md_file in md_files:
        rel_path = md_file.relative_to(docs_dir)
        blocks = extract_runnable_blocks(md_file)

        if not blocks:
            continue

        print(f"\n📄 {rel_path}")

        for line_num, code in blocks:
            total_blocks += 1

            # Skip examples that are supposed to fail
            if is_example_that_should_fail(code):
                print(f"  ⊘  Line {line_num}: Skipped (error example)")
                skipped += 1
                continue

            # Try to run it
            success, output = run_code_block(code, setup)

            if success:
                print(f"  ✅ Line {line_num}: Passed")
                passed += 1
            else:
                print(f"  ❌ Line {line_num}: Failed")
                print(f"     {output.split(chr(10))[0]}")  # First line of error
                failed += 1

    # Summary
    print()
    print("=" * 70)
    print("Summary")
    print("=" * 70)
    print(f"Total runnable blocks: {total_blocks}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print(f"Skipped (error examples): {skipped}")
    print()

    if failed > 0:
        print("❌ Some examples failed to run")
        print("\nNote: This is a basic runner. Some examples may fail because:")
        print("  - They depend on previous examples in the same file")
        print("  - They require specific setup (tables, data, etc.)")
        print("  - They're partial snippets, not complete programs")
        print("\nConsider using pytest-examples for more sophisticated testing.")
        sys.exit(1)
    else:
        print("✅ All runnable examples passed!")
        sys.exit(0)


if __name__ == "__main__":
    main()
