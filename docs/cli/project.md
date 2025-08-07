# Project Commands

## init

Initialize a new CinchDB project.

### Usage

```bash
cinch init [PATH] [OPTIONS]
```

### Arguments

- `PATH` - Directory to initialize (optional, defaults to current directory)

### Options

- `--database`, `-d` - Initial database name (default: "main")
- `--branch`, `-b` - Initial branch name (default: "main")

### Description

Creates a new CinchDB project with:
- `.cinchdb/` directory
- `config.toml` configuration file
- Initial database with specified name
- Initial branch with specified name
- Default `main` tenant with proper SQLite PRAGMAs

### Examples

```bash
# Initialize in current directory with defaults
cinch init

# Initialize in specific directory
cinch init myproject

# Initialize with custom database name
cinch init myapp --database production

# Initialize with custom database and branch
cinch init myapp --database mydb --branch dev

# Initialize and enter directory
cinch init myapp && cd myapp
```

### Project Structure

After initialization:

```
myproject/
└── .cinchdb/
    ├── config.toml
    └── databases/
        └── main/
            └── branches/
                └── main/
                    ├── metadata.json
                    ├── changes.json
                    └── tenants/
                        └── main.db
```

### Configuration File

The `config.toml` file contains:

```toml
active_database = "main"
active_branch = "main"

[remotes]
# Remote configurations will be added here
```

### Notes

- Cannot initialize in a directory that already contains `.cinchdb/`
- The project directory can be anywhere on your filesystem
- All CinchDB commands must be run from within a project directory

### Next Steps

After initialization:
- Create tables with [`cinch table create`](table.md#create)
- Create branches with [`cinch branch create`](branch.md#create)
- Add tenants with [`cinch tenant create`](tenant.md#create)