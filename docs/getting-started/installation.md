# Installation

CinchDB requires Python 3.10 or higher.

## Recommended: Install with uv

We recommend using [uv](https://docs.astral.sh/uv/) for faster installation and better dependency resolution:

```bash
# Install uv if you haven't already
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install CinchDB
uv add cinchdb
```

## Install with pip

Alternatively, install with pip:

```bash
pip install cinchdb
```

## Install from Source

For development or to get the latest features:

```bash
git clone https://github.com/russellromney/cinchdb.git
cd cinchdb

# With uv (recommended)
uv pip install -e .

# Or with pip
pip install -e .
```

## Verify Installation

Check that CinchDB is installed correctly:

```bash
cinch version
```

## Optional Dependencies


### Development

For development and testing:

```bash
# With uv (recommended)
uv add "cinchdb[dev]"

# Or with pip
pip install "cinchdb[dev]"
```

## System Requirements

- Python 3.10 or higher
- SQLite 3.35+ (included with Python)
- 10MB+ free disk space
- **Recommended**: [uv](https://docs.astral.sh/uv/) for faster package management

## Next Steps

- [Quick Start Guide](quickstart.md)
- [Core Concepts](concepts.md)