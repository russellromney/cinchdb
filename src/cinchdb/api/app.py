"""FastAPI application for CinchDB."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from cinchdb import __version__
from cinchdb.api.routers import (
    auth,
    projects,
    databases,
    branches,
    tenants,
    tables,
    columns,
    views,
    query
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    print(f"Starting CinchDB API v{__version__}")
    yield
    # Shutdown
    print("Shutting down CinchDB API")


# Create FastAPI app
app = FastAPI(
    title="CinchDB API",
    description="Git-like SQLite database management system",
    version=__version__,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(projects.router, prefix="/api/v1/projects", tags=["projects"])
app.include_router(databases.router, prefix="/api/v1/databases", tags=["databases"])
app.include_router(branches.router, prefix="/api/v1/branches", tags=["branches"])
app.include_router(tenants.router, prefix="/api/v1/tenants", tags=["tenants"])
app.include_router(tables.router, prefix="/api/v1/tables", tags=["tables"])
app.include_router(columns.router, prefix="/api/v1/columns", tags=["columns"])
app.include_router(views.router, prefix="/api/v1/views", tags=["views"])
app.include_router(query.router, prefix="/api/v1/query", tags=["query"])


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "CinchDB API",
        "version": __version__,
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}