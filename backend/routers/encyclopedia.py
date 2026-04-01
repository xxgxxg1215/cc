"""
/api/encyclopedia — 农业百科 / 病害图鉴
"""
import json

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from database import get_db
from models import Encyclopedia

router = APIRouter(prefix="/api/encyclopedia", tags=["百科"])

# ── 作物分类映射 ──
CROP_MAP = {
    "Apple": "苹果", "Blueberry": "蓝莓", "Cherry": "樱桃",
    "Corn": "玉米", "Grape": "葡萄", "Orange": "柑橘",
    "Peach": "桃", "Pepper": "甜椒", "Potato": "马铃薯",
    "Raspberry": "树莓", "Soybean": "大豆", "Squash": "南瓜",
    "Strawberry": "草莓", "Tomato": "番茄",
}


@router.get("/crops")
async def list_crops(db: Session = Depends(get_db)):
    """获取所有作物分类"""
    crops = (
        db.query(Encyclopedia.crop_name)
        .distinct()
        .all()
    )
    return {"crops": [c[0] for c in crops]}


@router.get("/list")
async def list_encyclopedia(
    crop: str = "",
    keyword: str = "",
    db: Session = Depends(get_db),
):
    """按作物筛选或关键词搜索"""
    query = db.query(Encyclopedia)
    if crop:
        query = query.filter(Encyclopedia.crop_name == crop)
    if keyword:
        query = query.filter(
            Encyclopedia.disease_name.contains(keyword)
            | Encyclopedia.description.contains(keyword)
        )
    items = query.order_by(Encyclopedia.crop_name, Encyclopedia.id).all()
    return {
        "list": [
            {
                "id": item.id,
                "crop_name": item.crop_name,
                "disease_name": item.disease_name,
                "disease_en": item.disease_en,
                "description": item.description[:80] + "…" if len(item.description) > 80 else item.description,
                "image_url": item.image_url,
            }
            for item in items
        ]
    }


@router.get("/detail/{item_id}")
async def get_detail(item_id: int, db: Session = Depends(get_db)):
    """获取百科详情"""
    item = db.query(Encyclopedia).filter(Encyclopedia.id == item_id).first()
    if not item:
        return {"error": "未找到该百科条目"}
    return {
        "id": item.id,
        "crop_name": item.crop_name,
        "disease_name": item.disease_name,
        "disease_en": item.disease_en,
        "description": item.description,
        "symptoms": item.symptoms,
        "cause": item.cause,
        "prevention": json.loads(item.prevention) if item.prevention else [],
        "medicine": json.loads(item.medicine) if item.medicine else [],
        "image_url": item.image_url,
    }
