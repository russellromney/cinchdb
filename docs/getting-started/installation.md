# Installation

CinchDB requires Python 3.10 or higher.

## Install from PyPI

The simplest way to install CinchDB:

```bash
pip install cinchdb
```

## Install from Source

For development or to get the latest features:

```bash
git clone https://github.com/russellromney/cinchdb.git
cd cinchdb
pip install -e .
```

## Verify Installation

Check that CinchDB is installed correctly:

```bash
cinch version
```

## Optional Dependencies

### API Server

To run the CinchDB API server, install with server extras:

```bash
pip install cinchdb[server]
```

### Development

For development and testing:

```bash
pip install cinchdb[dev]
```

## System Requirements

- Python 3.10 or higher
- SQLite 3.35+ (included with Python)
- 10MB+ free disk space

## Next Steps

- [Quick Start Guide](quickstart.md)
- [Core Concepts](concepts.md)