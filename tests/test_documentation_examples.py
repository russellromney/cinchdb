"""
Test that documentation examples actually work.

Uses pytest-examples to extract and run code from markdown docs.
Install: uv add --dev pytest-examples
Run: uv run pytest tests/test_documentation_examples.py -v
"""

import pytest
from pathlib import Path

# Conditional import - only run if pytest-examples is available
pytest_examples = pytest.importorskip("pytest_examples")
from pytest_examples import find_examples, CodeExample, EvalExample


# Get docs directory
DOCS_DIR = Path(__file__).parent.parent / "docs" / "python-sdk"


def get_examples():
    """Find all Python examples in python-sdk docs."""
    if not DOCS_DIR.exists():
        return []

    examples = []
    for md_file in DOCS_DIR.glob("*.md"):
        # Find Python code blocks in this file
        for example in find_examples(md_file, skip=["no-test"]):
            examples.append((md_file.name, example))

    return examples


@pytest.mark.parametrize("file_name,example", get_examples())
def test_documentation_example(file_name: str, example: CodeExample, tmp_path):
    """Test that each documentation example runs successfully.

    This test:
    1. Extracts Python code blocks from markdown
    2. Sets up an isolated test environment
    3. Runs the code
    4. Verifies it doesn't raise exceptions

    To skip an example, add <!-- no-test --> before the code block.
    """
    # Setup isolated environment
    import os
    os.chdir(tmp_path)

    # Initialize cinchdb project
    (tmp_path / ".cinchdb").mkdir(exist_ok=True)

    # Run the example
    # Note: Some examples may fail if they depend on context from previous examples
    # For a production test suite, you'd want to:
    # 1. Group related examples together
    # 2. Provide fixtures for common setup (tables, data, etc.)
    # 3. Use snapshot testing for expected outputs

    example.run_print_check()  # This will raise if the code fails


# Alternative: Manual test without pytest-examples dependency
@pytest.mark.skip(reason="Use pytest-examples version above")
def test_basic_api_signatures():
    """Basic smoke test that main APIs work with documented signatures."""
    import tempfile
    import cinchdb
    from cinchdb.models import Column

    with tempfile.TemporaryDirectory() as tmp:
        # Initialize
        db = cinchdb.CinchDB(database="test", branch="main", tenant="main", project_dir=tmp)

        # Create table
        db.create_table("users", [
            Column(name="name", type="TEXT"),
            Column(name="email", type="TEXT", unique=True)
        ])

        # Insert (new signature)
        user = db.insert("users", {"name": "Alice", "email": "alice@example.com"})
        assert "id" in user

        # Update (new signature - dict with id)
        updated = db.update("users", {"id": user["id"], "name": "Alice Smith"})
        assert updated["name"] == "Alice Smith"

        # Query
        results = db.query("SELECT * FROM users WHERE name = ?", ["Alice Smith"])
        assert len(results) == 1

        # Delete
        count = db.delete("users", user["id"])
        assert count == 1

        # Batch operations
        users = db.insert("users",
            {"name": "Bob", "email": "bob@example.com"},
            {"name": "Carol", "email": "carol@example.com"}
        )
        assert len(users) == 2

        # Create index (new signature)
        idx_name = db.create_index("users", ["email"], name="idx_email", unique=True)
        assert "idx_email" in idx_name or "email" in idx_name


if __name__ == "__main__":
    # Run the basic test without pytest-examples
    test_basic_api_signatures()
    print("✅ Basic API signatures work correctly!")
