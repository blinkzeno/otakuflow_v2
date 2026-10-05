"""Page endpoints: detail and image bytes served by id."""

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from backend.db.queries import pages as page_queries
from backend.storage import paths

router = APIRouter()

MEDIA_TYPES = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
}


@router.get("/api/pages/{page_id}")
def get_page(page_id: int) -> dict:
    page = page_queries.get_page(page_id)
    if page is None:
        raise HTTPException(status_code=404, detail="page not found")
    return page


@router.get("/api/pages/{page_id}/image")
def get_page_image(page_id: int, thumb: bool = False) -> FileResponse:
    page = page_queries.get_page(page_id)
    if page is None:
        raise HTTPException(status_code=404, detail="page not found")
    rel = str(page["rel_path"])
    if thumb:
        rel = rel.replace("/pages/", "/thumbs/")
    file_path = paths.safe_join(*rel.split("/"))
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="image file missing")
    return FileResponse(
        file_path, media_type=MEDIA_TYPES.get(file_path.suffix.lower(), "image/jpeg")
    )
