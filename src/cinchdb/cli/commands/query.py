"""Query execution command for CinchDB CLI."""

import typer
import json
from typing import Optional
from pathlib import Path
from rich.console import Console
from rich.table import Table as RichTable

from cinchdb.core.path_utils import get_tenant_db_path
from cinchdb.core.connection import DatabaseConnection
from cinchdb.cli.utils import get_config_with_data

app = typer.Typer(help="Execute SQL queries", invoke_without_command=True)
console = Console()


@app.callback()
def callback(ctx: typer.Context):
    """Show help when no subcommand is provided."""
    if ctx.invoked_subcommand is None:
        console.print(ctx.get_help())
        raise typer.Exit(0)


@app.command()
def execute(
    sql: str = typer.Argument(..., help="SQL query to execute"),
    tenant: Optional[str] = typer.Option("main", "--tenant", "-t", help="Tenant name"),
    format: Optional[str] = typer.Option("table", "--format", "-f", help="Output format (table, json, csv)"),
    limit: Optional[int] = typer.Option(None, "--limit", "-l", help="Limit number of rows")
):
    """Execute a SQL query.
    
    Examples:
        cinch query "SELECT * FROM users"
        cinch query "SELECT * FROM users WHERE active = 1" --format json
        cinch query "SELECT COUNT(*) FROM posts" --tenant tenant1
    """
    config, config_data = get_config_with_data()
    db_name = config_data.active_database
    branch_name = config_data.active_branch
    
    # Add LIMIT if specified
    query_sql = sql
    if limit and "LIMIT" not in sql.upper():
        query_sql = f"{sql} LIMIT {limit}"
    
    # Get database path
    db_path = get_tenant_db_path(config.project_dir, db_name, branch_name, tenant)
    
    try:
        with DatabaseConnection(db_path) as conn:
            cursor = conn.execute(query_sql)
            
            # Check if this is a SELECT query
            is_select = query_sql.strip().upper().startswith('SELECT')
            
            if is_select:
                rows = cursor.fetchall()
                
                if not rows:
                    console.print("[yellow]No results[/yellow]")
                    return
                
                # Get column names
                columns = [desc[0] for desc in cursor.description]
            
                if format == "json":
                    # JSON output
                    result = []
                    for row in rows:
                        result.append(dict(zip(columns, row)))
                    console.print_json(data=result)
                    
                elif format == "csv":
                    # CSV output
                    import csv
                    import sys
                    writer = csv.writer(sys.stdout)
                    writer.writerow(columns)
                    for row in rows:
                        writer.writerow(row)
                        
                else:
                    # Table output (default)
                    table = RichTable(title=f"Query Results ({len(rows)} rows)")
                    
                    # Add columns
                    for col in columns:
                        table.add_column(col, style="cyan")
                    
                    # Add rows
                    for row in rows:
                        # Convert all values to strings
                        str_row = [str(val) if val is not None else "NULL" for val in row]
                        table.add_row(*str_row)
                    
                    console.print(table)
            else:
                # For INSERT/UPDATE/DELETE, commit and show affected rows
                conn.commit()
                affected = cursor.rowcount
                console.print(f"[green]✅ Query executed successfully. Rows affected: {affected}[/green]")
                return
                
    except Exception as e:
        console.print(f"[red]❌ Query error: {e}[/red]")
        raise typer.Exit(1)