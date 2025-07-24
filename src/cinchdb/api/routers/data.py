"""Data CRUD router for CinchDB API."""

from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Path
from pydantic import BaseModel, Field

from cinchdb.core.database import CinchDB
from cinchdb.api.auth import AuthContext, require_write_permission, require_read_permission


router = APIRouter()


class DataRecord(BaseModel):
    """Generic data record with dynamic fields."""
    data: Dict[str, Any] = Field(description="Record data as key-value pairs")
    
    class Config:
        extra = "allow"


class CreateDataRequest(BaseModel):
    """Request to create a new data record."""
    data: Dict[str, Any] = Field(description="Record data as key-value pairs")


class UpdateDataRequest(BaseModel):
    """Request to update an existing data record."""
    data: Dict[str, Any] = Field(description="Record data to update")


class BulkCreateRequest(BaseModel):
    """Request to create multiple records."""
    records: List[Dict[str, Any]] = Field(description="List of records to create")


class FilterParams(BaseModel):
    """Query parameters for filtering data."""
    limit: Optional[int] = Field(None, description="Maximum number of records to return")
    offset: Optional[int] = Field(None, description="Number of records to skip")
    filters: Optional[Dict[str, Any]] = Field(None, description="Column filters")


def parse_query_filters(
    limit: Optional[int] = Query(None, description="Maximum number of records to return"),
    offset: Optional[int] = Query(None, description="Number of records to skip"),
    **query_params
) -> Dict[str, Any]:
    """Parse query parameters into filters dictionary."""
    filters = {}
    
    # Remove pagination params and non-filter params
    excluded_params = {'limit', 'offset', 'database', 'branch', 'tenant'}
    
    for key, value in query_params.items():
        if key not in excluded_params and value is not None:
            filters[key] = value
    
    return {
        'limit': limit,
        'offset': offset,
        'filters': filters
    }


# Helper function to create a generic Pydantic model for a table
def create_table_model(table_name: str) -> type:
    """Create a generic Pydantic model for a table."""
    return type(
        f"Table_{table_name}",
        (BaseModel,),
        {
            "__annotations__": {"data": Dict[str, Any]},
            "Config": type("Config", (), {
                "extra": "allow",
                "json_schema_extra": {"table_name": table_name}
            })
        }
    )


@router.get("/{table_name}/data", response_model=List[Dict[str, Any]])
async def list_table_data(
    table_name: str = Path(..., description="Table name"),
    database: str = Query(..., description="Database name"),
    branch: str = Query(..., description="Branch name"),
    tenant: str = Query(..., description="Tenant name"),
    limit: Optional[int] = Query(None, description="Maximum number of records to return"),
    offset: Optional[int] = Query(None, description="Number of records to skip"),
    auth: AuthContext = Depends(require_read_permission)
):
    """List all records in a table with optional filtering and pagination."""
    db_name = database
    branch_name = branch
    
    # Check branch permissions
    await require_read_permission(auth, branch_name)
    
    try:
        # Create CinchDB instance
        db = CinchDB(database=db_name, branch=branch_name, tenant=tenant, project_dir=auth.project_dir)
        
        # Verify table exists
        db.tables.get_table(table_name)  # This will raise ValueError if table doesn't exist
        
        # Create a generic model for the table
        table_model = create_table_model(table_name)
        
        # Parse filters from query parameters
        # For simplicity, we'll handle basic filters directly in the query
        # More complex filtering with operators would require parameter parsing
        filters = {}
        
        # Get records
        records = db.data.select(table_model, limit=limit, offset=offset, **filters)
        
        # Convert to dict format for response
        return [record.model_dump() if hasattr(record, 'model_dump') else record.__dict__ for record in records]
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{table_name}/data/{record_id}", response_model=Dict[str, Any])
async def get_record_by_id(
    table_name: str = Path(..., description="Table name"),
    record_id: str = Path(..., description="Record ID"),
    database: str = Query(..., description="Database name"),
    branch: str = Query(..., description="Branch name"),
    tenant: str = Query(..., description="Tenant name"),
    auth: AuthContext = Depends(require_read_permission)
):
    """Get a specific record by ID."""
    db_name = database
    branch_name = branch
    
    # Check branch permissions
    await require_read_permission(auth, branch_name)
    
    try:
        # Create CinchDB instance
        db = CinchDB(database=db_name, branch=branch_name, tenant=tenant, project_dir=auth.project_dir)
        
        # Verify table exists
        db.tables.get_table(table_name)
        
        table_model = create_table_model(table_name)
        
        record = db.data.find_by_id(table_model, record_id)
        
        if not record:
            raise HTTPException(status_code=404, detail=f"Record with ID {record_id} not found")
        
        return record.model_dump() if hasattr(record, 'model_dump') else record.__dict__
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{table_name}/data", response_model=Dict[str, Any])
async def create_record(
    request: CreateDataRequest,
    table_name: str = Path(..., description="Table name"), 
    database: str = Query(..., description="Database name"),
    branch: str = Query(..., description="Branch name"),
    tenant: str = Query(..., description="Tenant name"),
    auth: AuthContext = Depends(require_write_permission)
):
    """Create a new record in the table."""
    db_name = database
    branch_name = branch
    
    # Check branch permissions
    await require_write_permission(auth, branch_name)
    
    try:
        # Create CinchDB instance
        db = CinchDB(database=db_name, branch=branch_name, tenant=tenant, project_dir=auth.project_dir)
        
        # Verify table exists
        db.tables.get_table(table_name)
        
        table_model = create_table_model(table_name)
        
        # Create model instance from request data
        instance = table_model(**request.data)
        
        # Create the record
        created_record = db.data.create(instance)
        
        return created_record.model_dump() if hasattr(created_record, 'model_dump') else created_record.__dict__
        
    except ValueError as e:
        if "already exists" in str(e):
            raise HTTPException(status_code=409, detail=str(e))
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{table_name}/data/{record_id}", response_model=Dict[str, Any])
async def update_record(
    request: UpdateDataRequest,
    table_name: str = Path(..., description="Table name"),
    record_id: str = Path(..., description="Record ID"),
    database: str = Query(..., description="Database name"),
    branch: str = Query(..., description="Branch name"),
    tenant: str = Query(..., description="Tenant name"),
    auth: AuthContext = Depends(require_write_permission)
):
    """Update an existing record."""
    db_name = database
    branch_name = branch
    
    # Check branch permissions
    await require_write_permission(auth, branch_name)
    
    try:
        # Create CinchDB instance
        db = CinchDB(database=db_name, branch=branch_name, tenant=tenant, project_dir=auth.project_dir)
        
        # Verify table exists
        db.tables.get_table(table_name)
        
        table_model = create_table_model(table_name)
        
        # Ensure the ID is in the data
        update_data = request.data.copy()
        update_data["id"] = record_id
        
        # Create model instance
        instance = table_model(**update_data)
        
        # Update the record
        updated_record = db.data.update(instance)
        
        return updated_record.model_dump() if hasattr(updated_record, 'model_dump') else updated_record.__dict__
        
    except ValueError as e:
        if "not found" in str(e):
            raise HTTPException(status_code=404, detail=str(e))
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{table_name}/data/{record_id}")
async def delete_record(
    table_name: str = Path(..., description="Table name"),
    record_id: str = Path(..., description="Record ID"),
    database: str = Query(..., description="Database name"),
    branch: str = Query(..., description="Branch name"),
    tenant: str = Query(..., description="Tenant name"),
    auth: AuthContext = Depends(require_write_permission)
):
    """Delete a specific record by ID."""
    db_name = database
    branch_name = branch
    
    # Check branch permissions
    await require_write_permission(auth, branch_name)
    
    try:
        # Create CinchDB instance
        db = CinchDB(database=db_name, branch=branch_name, tenant=tenant, project_dir=auth.project_dir)
        
        # Verify table exists
        db.tables.get_table(table_name)
        
        table_model = create_table_model(table_name)
        
        # Delete the record
        deleted = db.data.delete_by_id(table_model, record_id)
        
        if not deleted:
            raise HTTPException(status_code=404, detail=f"Record with ID {record_id} not found")
        
        return {"message": f"Deleted record {record_id} from table '{table_name}'"}
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{table_name}/data/bulk", response_model=List[Dict[str, Any]])
async def bulk_create_records(
    request: BulkCreateRequest,
    table_name: str = Path(..., description="Table name"),
    database: str = Query(..., description="Database name"),
    branch: str = Query(..., description="Branch name"),
    tenant: str = Query(..., description="Tenant name"),
    auth: AuthContext = Depends(require_write_permission)
):
    """Create multiple records in a single transaction."""
    db_name = database
    branch_name = branch
    
    # Check branch permissions
    await require_write_permission(auth, branch_name)
    
    try:
        # Create CinchDB instance
        db = CinchDB(database=db_name, branch=branch_name, tenant=tenant, project_dir=auth.project_dir)
        
        # Verify table exists
        db.tables.get_table(table_name)
        
        table_model = create_table_model(table_name)
        
        # Create model instances from request data
        instances = [table_model(**record_data) for record_data in request.records]
        
        # Bulk create
        created_records = db.data.bulk_create(instances)
        
        return [record.model_dump() if hasattr(record, 'model_dump') else record.__dict__ 
                for record in created_records]
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{table_name}/data")
async def delete_records_with_filters(
    table_name: str = Path(..., description="Table name"),
    database: str = Query(..., description="Database name"),
    branch: str = Query(..., description="Branch name"),
    tenant: str = Query(..., description="Tenant name"),
    auth: AuthContext = Depends(require_write_permission),
    **query_params  # This will capture any additional query parameters as filters
):
    """Delete records matching filters. Requires at least one filter parameter."""
    db_name = database
    branch_name = branch
    
    # Check branch permissions
    await require_write_permission(auth, branch_name)
    
    # Extract filters from query parameters
    filters = {}
    excluded_params = {'database', 'branch', 'tenant'}
    
    for key, value in query_params.items():
        if key not in excluded_params and value is not None:
            filters[key] = value
    
    if not filters:
        raise HTTPException(
            status_code=400, 
            detail="At least one filter parameter is required to prevent accidental deletion of all records"
        )
    
    try:
        # Create CinchDB instance
        db = CinchDB(database=db_name, branch=branch_name, tenant=tenant, project_dir=auth.project_dir)
        
        # Verify table exists
        db.tables.get_table(table_name)
        
        table_model = create_table_model(table_name)
        
        # Delete records with filters
        deleted_count = db.data.delete(table_model, **filters)
        
        return {"message": f"Deleted {deleted_count} records from table '{table_name}'", "count": deleted_count}
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{table_name}/data/count")
async def count_records(
    table_name: str = Path(..., description="Table name"),
    database: str = Query(..., description="Database name"),
    branch: str = Query(..., description="Branch name"),
    tenant: str = Query(..., description="Tenant name"),
    auth: AuthContext = Depends(require_read_permission),
    **query_params  # This will capture any additional query parameters as filters
):
    """Count records in a table with optional filtering."""
    db_name = database
    branch_name = branch
    
    # Check branch permissions
    await require_read_permission(auth, branch_name)
    
    # Extract filters from query parameters
    filters = {}
    excluded_params = {'database', 'branch', 'tenant'}
    
    for key, value in query_params.items():
        if key not in excluded_params and value is not None:
            filters[key] = value
    
    try:
        # Create CinchDB instance
        db = CinchDB(database=db_name, branch=branch_name, tenant=tenant, project_dir=auth.project_dir)
        
        # Verify table exists
        db.tables.get_table(table_name)
        
        table_model = create_table_model(table_name)
        
        # Count records
        count = db.data.count(table_model, **filters)
        
        return {"count": count, "table": table_name, "filters": filters}
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))