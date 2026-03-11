"""
Keywords CRUD and import. See docs/05_API_DESIGN.md.
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db
from models.keyword import Keyword, KeywordCreate, KeywordResponse, KeywordUpdate

router = APIRouter(prefix="/keywords", tags=["Keywords"])


@router.get("", response_model=dict)
def list_keywords(
    status: Optional[str] = Query(None, description="Filter by status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """List keywords with optional status filter and pagination."""
    base = select(Keyword)
    if status:
        base = base.where(Keyword.status == status)
    total = db.execute(select(func.count()).select_from(base.subquery())).scalar() or 0
    q = base.order_by(Keyword.created_at.desc()).offset(skip).limit(limit)
    rows = db.execute(q).scalars().all()
    return {"items": [KeywordResponse.model_validate(r) for r in rows], "total": total}


@router.get("/{keyword_id}", response_model=KeywordResponse)
def get_keyword(keyword_id: int, db: Session = Depends(get_db)):
    """Get a single keyword by ID."""
    row = db.get(Keyword, keyword_id)
    if not row:
        raise HTTPException(status_code=404, detail="Keyword not found")
    return KeywordResponse.model_validate(row)


@router.post("", response_model=KeywordResponse, status_code=201)
def create_keyword(body: KeywordCreate, db: Session = Depends(get_db)):
    """Add a single keyword."""
    existing = db.execute(select(Keyword).where(Keyword.keyword == body.keyword.strip())).scalars().first()
    if existing:
        raise HTTPException(status_code=400, detail="Keyword already exists")
    kw = Keyword(keyword=body.keyword.strip(), status="pending")
    db.add(kw)
    db.commit()
    db.refresh(kw)
    return KeywordResponse.model_validate(kw)


@router.patch("/{keyword_id}", response_model=KeywordResponse)
def update_keyword(keyword_id: int, body: KeywordUpdate, db: Session = Depends(get_db)):
    """Update a keyword (partial)."""
    kw = db.get(Keyword, keyword_id)
    if not kw:
        raise HTTPException(status_code=404, detail="Keyword not found")
    data = body.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(kw, k, v)
    db.commit()
    db.refresh(kw)
    return KeywordResponse.model_validate(kw)


@router.delete("/{keyword_id}", status_code=204)
def delete_keyword(keyword_id: int, db: Session = Depends(get_db)):
    """Delete a keyword."""
    kw = db.get(Keyword, keyword_id)
    if not kw:
        raise HTTPException(status_code=404, detail="Keyword not found")
    db.delete(kw)
    db.commit()
    return None


@router.post("/import", response_model=dict)
def import_keywords(file: UploadFile, db: Session = Depends(get_db)):
    """Import keywords from a text or CSV file (one keyword per line or comma-separated)."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file")
    content = file.file.read().decode("utf-8", errors="replace")
    seen = set()
    added = 0
    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        for part in line.replace(",", " ").split():
            kw = part.strip()
            if kw and kw.lower() not in seen:
                seen.add(kw.lower())
                existing = db.execute(select(Keyword).where(Keyword.keyword == kw)).scalars().first()
                if not existing:
                    db.add(Keyword(keyword=kw, status="pending"))
                    added += 1
    db.commit()
    return {"imported": added, "total_unique": len(seen)}
