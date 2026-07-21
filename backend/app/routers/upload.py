from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import UploadResult
from app.services.import_service import import_file_bytes

router = APIRouter(prefix="/api/upload", tags=["upload"])


@router.post("/", response_model=UploadResult)
async def upload_file(file: UploadFile = File(...), db: Session = Depends(get_db)):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    lower = file.filename.lower()
    if not (lower.endswith(".csv") or lower.endswith((".xlsx", ".xls"))):
        raise HTTPException(
            status_code=400, detail="Only .csv and .xlsx files are accepted"
        )

    contents = await file.read()
    if len(contents) == 0:
        raise HTTPException(status_code=400, detail="Empty file")

    accepted, rejected, errors = import_file_bytes(
        contents, file.filename, db, source="upload"
    )
    db.commit()
    return UploadResult(rows_accepted=accepted, rows_rejected=rejected, errors=errors)
