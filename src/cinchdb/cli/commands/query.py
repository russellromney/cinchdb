"""Query execution command for CinchDB CLI."""

import typer
from typing import Optional
from rich.console import Console
from rich.table import Table as RichTable

from cinchdb.cli.utils import get_config_with_data
from cinchdb.managers.query import QueryManager

app = typer.Typer(help="Execute SQL queries", invoke_without_command=True)
console = Console()


def execute_query(sql: str, tenant: str, format: str, limit: Optional[int]):
    """Execute a SQL query."""
    config, config_data = get_config_with_data()
    db_name = config_data.active_database
    branch_name = config_data.active_branch

    # Add LIMIT if specified
    query_sql = sql
    if limit and "LIMIT" not in sql.upper():
        query_sql = f"{sql} LIMIT {limit}"

    # Create QueryManager
    query_manager = QueryManager(config.project_dir, db_name, branch_name, tenant)

    try:
        # Check if this is a SELECT query
        is_select = query_sql.strip().upper().startswith("SELECT")

        if is_select:
            # Execute SELECT query
            rows = query_manager.execute(query_sql)

            if not rows:
                console.print("[yellow]No results[/yellow]")
                return

            # Get column names from first row
            columns = list(rows[0].keys()) if rows else []

            if format == "json":
                # JSON output - rows are already dicts
                console.print_json(data=rows)

            elif format == "csv":
                # CSV output
                import csv
                import sys

                writer = csv.writer(sys.stdout)
                writer.writerow(columns)
                for row in rows:
                    writer.writerow([row[col] for col in columns])

            else:
                # Table output (default)
                table = RichTable(title=f"Query Results ({len(rows)} rows)")

                # Add columns
                for col in columns:
                    table.add_column(col, style="cyan")

                # Add rows
                for row in rows:
                    # Convert all values to strings
                    str_row = [
                        str(row[col]) if row[col] is not None else "NULL"
                        for col in columns
                    ]
                    table.add_row(*str_row)

                console.print(table)
        else:
            # For INSERT/UPDATE/DELETE, use execute_non_query
            affected = query_manager.execute_non_query(query_sql)
            console.print(
                f"[green]✅ Query executed successfully. Rows affected: {affected}[/green]"
            )

    except Exception as e:
        console.print(f"[red]❌ Query error: {e}[/red]")
        raise typer.Exit(1)


@app.callback()
def main(
    ctx: typer.Context,
    sql: Optional[str] = typer.Argument(None, help="SQL query to execute"),
    tenant: Optional[str] = typer.Option("main", "--tenant", "-t", help="Tenant name"),
    format: Optional[str] = typer.Option(
        "table", "--format", "-f", help="Output format (table, json, csv)"
    ),
    limit: Optional[int] = typer.Option(
        None, "--limit", "-l", help="Limit number of rows"
    ),
):
    """Execute a SQL query.

    Examples:
        cinch query "SELECT * FROM users"
        cinch query "SELECT * FROM users WHERE active = 1" --format json
        cinch query "SELECT COUNT(*) FROM posts" --tenant tenant1
    """
    # If no subcommand is invoked and we have SQL, execute it
    if ctx.invoked_subcommand is None:
        if not sql:
            console.print(ctx.get_help())
            raise typer.Exit(0)
        execute_query(sql, tenant, format, limit)
