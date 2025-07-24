"""Code generation router for CinchDB API."""

import zipfile
import tempfile
from typing import List, Dict
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel

from cinchdb.managers.codegen import CodegenManager
from cinchdb.api.auth import AuthContext, require_read_permission


router = APIRouter()


class CodegenLanguage(BaseModel):
    """Supported language for code generation."""
    name: str
    description: str


class GenerateModelsRequest(BaseModel):
    """Request to generate models."""
    language: str
    include_tables: bool = True
    include_views: bool = True


class GenerateModelsResponse(BaseModel):
    """Response from model generation."""
    language: str
    files_generated: List[str]
    tables_processed: List[str]
    views_processed: List[str]
    download_url: str


@router.get("/languages", response_model=List[CodegenLanguage])
async def list_supported_languages(
    auth: AuthContext = Depends(require_read_permission)
):
    """List supported code generation languages."""
    # Using a temporary codegen manager to get supported languages
    # This doesn't require specific database/branch so we use dummy values
    temp_project = Path(tempfile.mkdtemp())
    try:
        codegen_mgr = CodegenManager(temp_project, "dummy", "dummy", "dummy")
        languages = codegen_mgr.get_supported_languages()
        
        # Map languages to descriptions
        language_info = {
            "python": "Python Pydantic models with full CRUD operations",
            "typescript": "TypeScript interfaces and classes (planned)"
        }
        
        return [
            CodegenLanguage(
                name=lang, 
                description=language_info.get(lang, f"{lang.title()} models")
            ) 
            for lang in languages
        ]
    finally:
        # Clean up temp directory
        import shutil
        shutil.rmtree(temp_project, ignore_errors=True)


@router.post("/generate", response_model=GenerateModelsResponse)
async def generate_models(
    request: GenerateModelsRequest,
    database: str = Query(..., description="Database name"),
    branch: str = Query(..., description="Branch name"),
    auth: AuthContext = Depends(require_read_permission)
):
    """Generate model files for the specified language and return as ZIP download."""
    db_name = database
    branch_name = branch
    
    # Check branch permissions
    await require_read_permission(auth, branch_name)
    
    try:
        # Create temporary directory for generation
        temp_dir = Path(tempfile.mkdtemp())
        output_dir = temp_dir / "generated_models"
        
        # Initialize codegen manager
        codegen_mgr = CodegenManager(auth.project_dir, db_name, branch_name, "main")
        
        # Generate models
        results = codegen_mgr.generate_models(
            language=request.language,
            output_dir=output_dir,
            include_tables=request.include_tables,
            include_views=request.include_views
        )
        
        # Create ZIP file with generated models
        zip_path = temp_dir / f"cinchdb_models_{request.language}.zip"
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file_name in results["files_generated"]:
                file_path = output_dir / file_name
                if file_path.exists():
                    # Add file to ZIP with just the filename (no directory structure)
                    zipf.write(file_path, file_name)
        
        # Store the ZIP file path for download (in a real implementation, 
        # you might want to use a more sophisticated temporary file management system)
        download_filename = f"cinchdb_models_{request.language}_{db_name}_{branch_name}.zip"
        
        # In a production system, you might store this in a cache or temporary storage
        # For now, we'll return the file directly
        
        return GenerateModelsResponse(
            language=results["language"],
            files_generated=results["files_generated"],
            tables_processed=results["tables_processed"],
            views_processed=results["views_processed"],
            download_url=f"/api/v1/codegen/download/{download_filename}"
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Code generation failed: {str(e)}")


@router.get("/generate/download/{filename}")
async def download_generated_models(
    filename: str,
    database: str = Query(..., description="Database name"),
    branch: str = Query(..., description="Branch name"),
    auth: AuthContext = Depends(require_read_permission)
):
    """Download previously generated model files as ZIP."""
    db_name = database
    branch_name = branch
    
    # Check branch permissions
    await require_read_permission(auth, branch_name)
    
    # Parse filename to extract language and validate request
    if not filename.startswith("cinchdb_models_"):
        raise HTTPException(status_code=400, detail="Invalid filename format")
    
    try:
        # Extract language from filename
        parts = filename.split("_")
        if len(parts) < 3:
            raise HTTPException(status_code=400, detail="Invalid filename format")
        
        language = parts[2]  # cinchdb_models_<language>_...
        
        # Re-generate the models (since we don't persist them)
        # In a production system, you might cache generated files
        temp_dir = Path(tempfile.mkdtemp())
        output_dir = temp_dir / "generated_models"
        
        # Initialize codegen manager
        codegen_mgr = CodegenManager(auth.project_dir, db_name, branch_name, "main")
        
        # Generate models
        results = codegen_mgr.generate_models(
            language=language,
            output_dir=output_dir,
            include_tables=True,
            include_views=True
        )
        
        # Create ZIP file
        zip_path = temp_dir / filename
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file_name in results["files_generated"]:
                file_path = output_dir / file_name
                if file_path.exists():
                    zipf.write(file_path, file_name)
        
        # Return ZIP file as download
        return FileResponse(
            path=str(zip_path),
            filename=filename,
            media_type="application/zip"
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Download failed: {str(e)}")


@router.post("/generate/files", response_model=Dict[str, str])
async def generate_model_files_content(
    request: GenerateModelsRequest,
    database: str = Query(..., description="Database name"),
    branch: str = Query(..., description="Branch name"),
    auth: AuthContext = Depends(require_read_permission)
):
    """Generate model files and return their content as JSON (alternative to ZIP download)."""
    db_name = database
    branch_name = branch
    
    # Check branch permissions
    await require_read_permission(auth, branch_name)
    
    try:
        # Create temporary directory for generation
        temp_dir = Path(tempfile.mkdtemp())
        output_dir = temp_dir / "generated_models"
        
        # Initialize codegen manager
        codegen_mgr = CodegenManager(auth.project_dir, db_name, branch_name, "main")
        
        # Generate models
        results = codegen_mgr.generate_models(
            language=request.language,
            output_dir=output_dir,
            include_tables=request.include_tables,
            include_views=request.include_views
        )
        
        # Read generated files and return their content
        file_contents = {}
        
        for file_name in results["files_generated"]:
            file_path = output_dir / file_name
            if file_path.exists():
                with open(file_path, 'r', encoding='utf-8') as f:
                    file_contents[file_name] = f.read()
        
        # Clean up temp directory
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)
        
        return file_contents
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Code generation failed: {str(e)}")


@router.get("/info")
async def get_codegen_info(
    database: str = Query(..., description="Database name"),
    branch: str = Query(..., description="Branch name"),
    auth: AuthContext = Depends(require_read_permission)
):
    """Get information about what can be generated for the current database/branch."""
    db_name = database
    branch_name = branch
    
    # Check branch permissions
    await require_read_permission(auth, branch_name)
    
    try:
        # Initialize codegen manager
        codegen_mgr = CodegenManager(auth.project_dir, db_name, branch_name, "main")
        
        # Get available tables and views
        tables = codegen_mgr.table_manager.list_tables()
        views = codegen_mgr.view_manager.list_views()
        
        return {
            "database": db_name,
            "branch": branch_name,
            "tenant": tenant,
            "supported_languages": codegen_mgr.get_supported_languages(),
            "available_tables": [table.name for table in tables],
            "available_views": [view.name for view in views],
            "total_entities": len(tables) + len(views)
        }
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))