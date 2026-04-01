"""
/api/history — 云端识别历史
"""
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session
from sqlalchemy import desc

from database import get_db
from models import RecognitionHistory
from routers.user import parse_token

router = APIRouter(prefix="/api/history", tags=["历史记录"])


@router.get("/list")
async def list_history(
    request: Request,
    token: str = "",
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    db: Session = Depends(get_db),
):
    """分页获取识别历史"""
    user_id = parse_token(token)
    base = str(request.base_url).rstrip("/")
    query = (
        db.query(RecognitionHistory)
        .filter(RecognitionHistory.user_id == user_id)
        .order_by(desc(RecognitionHistory.created_at))
    )
    total = query.count()
    records = query.offset((page - 1) * page_size).limit(page_size).all()

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "list": [
            {
                "id": r.id,
                "image_url": base + r.image_url if r.image_url else "",
                "prediction": r.prediction,
                "disease_en": r.disease_en,
                "confidence": r.confidence,
                "is_healthy": r.is_healthy,
                "created_at": r.created_at.strftime("%Y-%m-%d %H:%M"),
            }
            for r in records
        ],
    }


@router.delete("/{record_id}")
async def delete_history(record_id: int, token: str = "", db: Session = Depends(get_db)):
    """删除一条历史"""
    user_id = parse_token(token)
    record = (
        db.query(RecognitionHistory)
        .filter(RecognitionHistory.id == record_id, RecognitionHistory.user_id == user_id)
        .first()
    )
    if not record:
        raise HTTPException(status_code=404, detail="记录不存在")
    db.delete(record)
    db.commit()
    return {"message": "删除成功"}


@router.delete("/")
async def clear_history(token: str = "", db: Session = Depends(get_db)):
    """清空所有历史"""
    user_id = parse_token(token)
    db.query(RecognitionHistory).filter(RecognitionHistory.user_id == user_id).delete()
    db.commit()
    return {"message": "已清空"}
