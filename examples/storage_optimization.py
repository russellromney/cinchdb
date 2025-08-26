#!/usr/bin/env python3
"""
Example of periodic storage optimization for CinchDB.

This script demonstrates how to run periodic optimization on all tenants
to keep databases compact and performant. In production, this could be
run as a cron job or background task.

The optimization process:
- Runs VACUUM on all tenants to reclaim space
- Adjusts page sizes as databases grow
- Keeps small databases compact with 512-byte pages
"""

import time
import logging
from pathlib import Path

from cinchdb.core.database import CinchDB


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def optimize_project_storage(project_dir: Path, dry_run: bool = False):
    """Optimize storage for all databases and branches in a project.
    
    Args:
        project_dir: Path to CinchDB project
        dry_run: If True, just report what would be optimized
    """
    logger.info(f"Starting storage optimization for project: {project_dir}")
    
    # List all databases using CinchDB
    databases = CinchDB.list_databases(project_dir)
    
    total_optimized = 0
    total_errors = 0
    
    for db_name in databases:
        logger.info(f"Processing database: {db_name}")
        
        # Connect to each database
        db = CinchDB(database=db_name, project_dir=project_dir)
        
        # Get all branches
        branches = db.list_branches()
        
        for branch_name in branches:
            logger.info(f"  Processing branch: {branch_name}")
            
            # Switch to branch
            db.use_branch(branch_name)
            
            # Get all tenants
            tenants = db.list_tenants()
            
            # Filter out system tenants
            user_tenants = [t for t in tenants if t not in ['main', '__empty__']]
            
            if dry_run:
                logger.info(f"    Would optimize {len(user_tenants)} tenants")
            else:
                # Optimize all tenants in this branch
                results = db.optimize_all_tenants()
                
                if results['optimized']:
                    logger.info(f"    Optimized: {', '.join(results['optimized'])}")
                    total_optimized += len(results['optimized'])
                
                if results['errors']:
                    for tenant_name, error in results['errors']:
                        logger.error(f"    Error optimizing {tenant_name}: {error}")
                    total_errors += len(results['errors'])
                    
                if not results['optimized'] and not results['errors']:
                    logger.info("    No tenants needed optimization")
    
    logger.info(f"Optimization complete. Optimized: {total_optimized}, Errors: {total_errors}")
    return total_optimized, total_errors


def run_periodic_optimization(project_dir: Path, interval_seconds: int = 60):
    """Run optimization periodically.
    
    Args:
        project_dir: Path to CinchDB project
        interval_seconds: How often to run optimization (default: 60 seconds)
    """
    logger.info(f"Starting periodic optimization every {interval_seconds} seconds")
    
    while True:
        try:
            start_time = time.time()
            optimized, errors = optimize_project_storage(project_dir)
            duration = time.time() - start_time
            
            logger.info(f"Optimization cycle completed in {duration:.2f} seconds")
            
            # Sleep until next interval
            sleep_time = max(0, interval_seconds - duration)
            if sleep_time > 0:
                logger.info(f"Sleeping for {sleep_time:.1f} seconds until next cycle")
                time.sleep(sleep_time)
                
        except KeyboardInterrupt:
            logger.info("Optimization stopped by user")
            break
        except Exception as e:
            logger.error(f"Unexpected error during optimization: {e}")
            time.sleep(interval_seconds)


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python storage_optimization.py <project_dir> [--dry-run] [--once]")
        print("\nOptions:")
        print("  --dry-run  Just report what would be optimized")
        print("  --once     Run optimization once and exit")
        sys.exit(1)
    
    project_dir = Path(sys.argv[1])
    dry_run = "--dry-run" in sys.argv
    run_once = "--once" in sys.argv
    
    if not project_dir.exists():
        print(f"Error: Project directory {project_dir} does not exist")
        sys.exit(1)
    
    if run_once:
        optimize_project_storage(project_dir, dry_run=dry_run)
    else:
        # Run every minute by default
        run_periodic_optimization(project_dir, interval_seconds=60)