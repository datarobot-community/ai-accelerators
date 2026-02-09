from pathlib import Path
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

router = APIRouter()

# Resolve paths
knowledge_base_dir = Path(__file__).resolve().parents[1] / "knowledge-base"
regulations_pdf_dir = Path(__file__).resolve().parents[1] / "regulations_pdf"



@router.get("/api/regulations_pdf/{filename}")
async def get_regulation_pdf(filename: str) -> FileResponse:
    """Serve a specific PDF file from the regulations_pdf directory by filename."""
    if ".." in filename or filename.startswith("/"):
        raise HTTPException(status_code=400, detail="Invalid filename")

    file_path = regulations_pdf_dir / filename
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="File not found")

    # # Default to application/pdf; clients rely on extension as well
    # return FileResponse(str(file_path), media_type="application/pdf", filename=filename)
    # Serve inline so browsers open in a new tab instead of forcing download
    return FileResponse(
        str(file_path),
        media_type="application/pdf",
        headers={"Content-Disposition": f"inline; filename=\"{filename}\""}
    )


