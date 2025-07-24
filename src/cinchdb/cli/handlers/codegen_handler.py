"""Unified codegen handler for local and remote operations."""

import requests
from pathlib import Path
from typing import Dict, Any, Optional, List
from rich.console import Console

from ...managers import CodegenManager

console = Console()


class CodegenHandler:
    """Handles both local and remote code generation operations."""

    def __init__(
        self,
        config_data: Dict[str, Any],
        api_url: Optional[str] = None,
        api_key: Optional[str] = None,
        force_local: bool = False,
    ):
        """Initialize the handler.

        Args:
            config_data: Configuration data from config.toml
            api_url: Optional API URL for remote generation
            api_key: Optional API key for remote generation
            force_local: Force local generation even if API configured
        """
        self.config_data = config_data
        self.force_local = force_local

        # Determine if we should use remote API
        self.api_url = api_url or config_data.get("api", {}).get("url")
        self.api_key = api_key or config_data.get("api", {}).get("key")
        self.is_remote = bool(self.api_url and self.api_key and not force_local)

    def generate_models(
        self,
        language: str,
        output_dir: Path,
        database: str,
        branch: str,
        tenant: str = "main",
        include_tables: bool = True,
        include_views: bool = True,
        project_root: Optional[Path] = None,
    ) -> Dict[str, Any]:
        """Generate models using local or remote approach.

        Returns:
            Dict with generation results in consistent format
        """
        if self.is_remote:
            return self._generate_remote(
                language=language,
                output_dir=output_dir,
                database=database,
                branch=branch,
                tenant=tenant,
                include_tables=include_tables,
                include_views=include_views,
            )
        else:
            return self._generate_local(
                language=language,
                output_dir=output_dir,
                database=database,
                branch=branch,
                tenant=tenant,
                include_tables=include_tables,
                include_views=include_views,
                project_root=project_root,
            )

    def _generate_local(
        self,
        language: str,
        output_dir: Path,
        database: str,
        branch: str,
        tenant: str = "main",
        include_tables: bool = True,
        include_views: bool = True,
        project_root: Optional[Path] = None,
    ) -> Dict[str, Any]:
        """Generate models locally using CodegenManager."""
        if not project_root:
            raise ValueError("project_root is required for local generation")

        manager = CodegenManager(
            project_root=project_root, database=database, branch=branch, tenant=tenant
        )

        return manager.generate_models(
            language=language,
            output_dir=output_dir,
            include_tables=include_tables,
            include_views=include_views,
        )

    def _generate_remote(
        self,
        language: str,
        output_dir: Path,
        database: str,
        branch: str,
        tenant: str = "main",
        include_tables: bool = True,
        include_views: bool = True,
    ) -> Dict[str, Any]:
        """Generate models remotely using API."""
        try:
            # Prepare request payload
            payload = {
                "language": language,
                "include_tables": include_tables,
                "include_views": include_views,
            }

            # Prepare query parameters - database and branch required, tenant not needed for codegen
            params = {"database": database, "branch": branch}

            # Make API request to generate files endpoint (returns JSON content)
            response = requests.post(
                f"{self.api_url}/api/v1/codegen/generate/files",
                json=payload,
                params=params,
                headers={"Authorization": f"Bearer {self.api_key}"},
            )
            response.raise_for_status()

            # Parse response
            result = response.json()
            files_data = result["files"]

            # Create output directory
            output_dir.mkdir(parents=True, exist_ok=True)

            # Write files to local filesystem
            files_generated = []
            for file_info in files_data:
                file_path = output_dir / file_info["filename"]
                file_path.write_text(file_info["content"])
                files_generated.append(file_info["filename"])

            # Return consistent format matching local generation
            return {
                "files_generated": files_generated,
                "tables_processed": result.get("tables_processed", []),
                "views_processed": result.get("views_processed", []),
                "output_dir": str(output_dir),
                "language": language,
                "remote": True,
            }

        except requests.RequestException as e:
            raise RuntimeError(f"Remote codegen failed: {e}")
        except KeyError as e:
            raise RuntimeError(f"Invalid API response format: missing {e}")

    def get_supported_languages(self, project_root: Optional[Path] = None) -> List[str]:
        """Get supported languages from local or remote source."""
        if self.is_remote:
            try:
                response = requests.get(
                    f"{self.api_url}/api/v1/codegen/languages",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                )
                response.raise_for_status()
                result = response.json()
                return [lang["name"] for lang in result["languages"]]
            except requests.RequestException:
                # Fall back to local if remote fails
                pass

        # Use local manager for supported languages
        if not project_root:
            # Return hardcoded list if no project available
            return ["python"]

        manager = CodegenManager(
            project_root=project_root,
            database=self.config_data.get("active_database", "main"),
            branch=self.config_data.get("active_branch", "main"),
            tenant="main",
        )
        return manager.get_supported_languages()
