"""
初始化数据库 — 将 disease_info.py 中的知识库导入 encyclopedia 表
运行: python init_db.py
"""
import json
from database import engine, Base, SessionLocal
from models import Encyclopedia
from disease_info import DISEASE_INFO

# 中文作物名提取
CROP_CN = {
    "Apple": "苹果", "Blueberry": "蓝莓", "Cherry": "樱桃",
    "Corn": "玉米", "Grape": "葡萄", "Orange": "柑橘",
    "Peach": "桃", "Pepper": "甜椒", "Potato": "马铃薯",
    "Raspberry": "树莓", "Soybean": "大豆", "Squash": "南瓜",
    "Strawberry": "草莓", "Tomato": "番茄",
}


def get_crop_name(disease_en: str) -> str:
    """从英文类名提取作物中文名"""
    for en, cn in CROP_CN.items():
        if disease_en.startswith(en):
            return cn
    return "其他"


def init_encyclopedia():
    """将 DISEASE_INFO 写入 encyclopedia 表"""
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    existing = db.query(Encyclopedia).count()
    if existing > 0:
        print(f"百科表中已有 {existing} 条数据，跳过初始化。如需重新导入请先清空表。")
        db.close()
        return

    count = 0
    for disease_en, info in DISEASE_INFO.items():
        item = Encyclopedia(
            crop_name=get_crop_name(disease_en),
            disease_name=info.get("name_cn", disease_en),
            disease_en=disease_en,
            description=info.get("description", ""),
            symptoms=info.get("symptoms", ""),
            cause=info.get("cause", ""),
            prevention=json.dumps(info.get("prevention", []), ensure_ascii=False),
            medicine=json.dumps(info.get("medicine", []), ensure_ascii=False),
        )
        db.add(item)
        count += 1

    db.commit()
    db.close()
    print(f"成功导入 {count} 条百科数据！")


if __name__ == "__main__":
    init_encyclopedia()
