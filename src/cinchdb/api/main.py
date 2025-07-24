"""Main API entry point for CinchDB."""

import uvicorn
from fastapi import FastAPI

app = FastAPI(
    title="CinchDB API",
    description="API for CinchDB - A Git-like SQLite database management system",
    version="0.1.0",
)


@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "Welcome to CinchDB API"}


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}


def start_server():
    """Start the API server."""
    uvicorn.run(
        "cinchdb.api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )


if __name__ == "__main__":
    start_server()