"""Query execution command for CinchDB CLI."""

import typer
from typing import Optional
from rich.console import Console
from rich.table import Table as RichTable

from cinchdb.cli.utils import get_cinchdb_instance

app = typer.Typer(help="Execute SQL queries", invoke_without_command=True)
console = Console()


def execute_query(
    sql: str,
    tenant: str,
    format: str,
    limit: Optional[int],
    force_local: bool = False,
    remote_alias: Optional[str] = None,
):
    """Execute a SQL query."""
    # Add LIMIT if specified
    query_sql = sql
    if limit and "LIMIT" not in sql.upper():
        query_sql = f"{sql} LIMIT {limit}"

    # Get CinchDB instance (handles local/remote automatically)
    db = get_cinchdb_instance(
        tenant=tenant, force_local=force_local, remote_alias=remote_alias
    )

    try:
        # Check if this is a SELECT query
        is_select = query_sql.strip().upper().startswith("SELECT")

        if is_select:
            # Execute SELECT query
            rows = db.query(query_sql)

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
            # For INSERT/UPDATE/DELETE, we need to handle local vs remote differently
            if db.is_local:
                # For local connections, use the query manager directly
                from cinchdb.managers.query import QueryManager

                query_mgr = QueryManager(db.project_dir, db.database, db.branch, tenant)
                affected_rows = query_mgr.execute_non_query(query_sql)
                console.print(
                    f"[green]✅ Query executed successfully[/green]\n"
                    f"[cyan]Rows affected: {affected_rows}[/cyan]"
                )
            else:
                # For remote connections, the API should handle all SQL types
                # This might need API support - for now, try using query
                try:
                    db.query(query_sql)
                    console.print("[green]✅ Query executed successfully[/green]")
                except Exception as e:
                    # If remote doesn't support non-SELECT via query, show helpful message
                    console.print(
                        f"[red]❌ Remote execution of non-SELECT queries may require API support[/red]\n"
                        f"[yellow]Error: {e}[/yellow]"
                    )
                    raise

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
    local: bool = typer.Option(False, "--local", "-L", help="Force local connection"),
    remote: Optional[str] = typer.Option(
        None, "--remote", "-r", help="Use specific remote alias"
    ),
):
    """Execute a SQL query.

    Examples:
        cinch query "SELECT * FROM users"
        cinch query "SELECT * FROM users WHERE active = 1" --format json
        cinch query "SELECT COUNT(*) FROM posts" --tenant tenant1
        cinch query "SELECT * FROM users" --remote production
        cinch query "SELECT * FROM users" --local
    """
    # If no subcommand is invoked and we have SQL, execute it
    if ctx.invoked_subcommand is None:
        if not sql:
            console.print(ctx.get_help())
            raise typer.Exit(0)
        execute_query(
            sql, tenant, format, limit, force_local=local, remote_alias=remote
        )
