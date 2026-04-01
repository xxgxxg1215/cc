"""
/api/news — 新闻资讯
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc

from database import get_db
from models import News

router = APIRouter(prefix="/api/news", tags=["资讯"])


@router.get("/list")
async def list_news(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    db: Session = Depends(get_db),
):
    """新闻列表（仅已发布）"""
    query = (
        db.query(News)
        .filter(News.is_published == True)
        .order_by(desc(News.created_at))
    )
    total = query.count()
    items = query.offset((page - 1) * page_size).limit(page_size).all()
    return {
        "total": total,
        "page": page,
        "list": [
            {
                "id": n.id,
                "title": n.title,
                "cover_image": n.cover_image,
                "author": n.author,
                "created_at": n.created_at.strftime("%Y-%m-%d"),
            }
            for n in items
        ],
    }


@router.get("/detail/{news_id}")
async def news_detail(news_id: int, db: Session = Depends(get_db)):
    """新闻详情"""
    news = db.query(News).filter(News.id == news_id, News.is_published == True).first()
    if not news:
        return {"error": "资讯不存在"}
    return {
        "id": news.id,
        "title": news.title,
        "content": news.content,
        "cover_image": news.cover_image,
        "author": news.author,
        "created_at": news.created_at.strftime("%Y-%m-%d %H:%M"),
    }
