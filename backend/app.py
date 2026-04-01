"""
农作物病害识别 - FastAPI 后端服务（模块化版本）
启动: uvicorn app:app --host 0.0.0.0 --port 8000
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from database import engine, Base
from config import UPLOAD_DIR

# 导入所有模型，确保 create_all 能发现
import models  # noqa

from routers import predict, user, history, encyclopedia, community, weather, news, admin, chat

# ── 建表 ──
Base.metadata.create_all(bind=engine)

# ── FastAPI 实例 ──
app = FastAPI(title="农作物病害识别 API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── 静态文件 ──
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

# ── 注册路由 ──
app.include_router(predict.router)
app.include_router(user.router)
app.include_router(history.router)
app.include_router(encyclopedia.router)
app.include_router(community.router)
app.include_router(weather.router)
app.include_router(news.router)
app.include_router(admin.router)
app.include_router(chat.router)
