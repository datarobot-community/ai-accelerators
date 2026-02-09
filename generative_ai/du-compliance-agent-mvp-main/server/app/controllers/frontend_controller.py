import os
from pathlib import Path
from fastapi import APIRouter
from fastapi.responses import FileResponse

router = APIRouter()

# This is the directory that contains the React build files
# Resolve relative to this file: server/app/frontend_dist
react_build_dir = str(Path(__file__).resolve().parents[1] / "frontend_dist")


@router.get("/")
async def serve_root() -> FileResponse:
    """Serve the React index.html for the root route."""
    return FileResponse(os.path.join(react_build_dir, "index.html"))


@router.get("/{path:path}")
async def serve_static_files(path: str) -> FileResponse:
    """
    Serve static files or fallback to React's index.html for unmatched routes.
    """
    file_path = os.path.join(react_build_dir, path)
    if os.path.exists(file_path):
        return FileResponse(file_path)
    return FileResponse(os.path.join(react_build_dir, "index.html"))
