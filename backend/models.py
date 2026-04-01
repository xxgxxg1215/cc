"""
数据库模型 — 所有表定义
"""
from datetime import datetime

from sqlalchemy import (
    Column, Integer, String, Text, Boolean, Float,
    DateTime, ForeignKey, UniqueConstraint,
)
from sqlalchemy.orm import relationship

from database import Base


# ── 用户表 ──
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    openid = Column(String(64), unique=True, nullable=False, index=True)
    nickname = Column(String(64), default="微信用户")
    avatar_url = Column(String(512), default="")
    role = Column(String(16), default="user")  # user / expert / admin
    created_at = Column(DateTime, default=datetime.now)

    histories = relationship("RecognitionHistory", back_populates="user")
    posts = relationship("Post", back_populates="user")
    comments = relationship("Comment", back_populates="user")


# ── 识别历史 ──
class RecognitionHistory(Base):
    __tablename__ = "recognition_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    image_url = Column(String(512), default="")
    prediction = Column(String(64), nullable=False)
    disease_en = Column(String(128), default="")
    confidence = Column(Float, default=0.0)
    is_healthy = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.now)

    user = relationship("User", back_populates="histories")


# ── 百科 ──
class Encyclopedia(Base):
    __tablename__ = "encyclopedia"

    id = Column(Integer, primary_key=True, autoincrement=True)
    crop_name = Column(String(32), nullable=False, index=True)   # 苹果、番茄 …
    disease_name = Column(String(64), nullable=False)            # 苹果黑星病
    disease_en = Column(String(128), unique=True, nullable=False)
    description = Column(Text, default="")
    symptoms = Column(Text, default="")
    cause = Column(Text, default="")
    prevention = Column(Text, default="")   # JSON array string
    medicine = Column(Text, default="")     # JSON array string
    image_url = Column(String(512), default="")


# ── 社区帖子 ──
class Post(Base):
    __tablename__ = "posts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String(128), nullable=False)
    content = Column(Text, default="")
    image_urls = Column(Text, default="")   # JSON array string
    like_count = Column(Integer, default=0)
    comment_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.now)

    user = relationship("User", back_populates="posts")
    comments = relationship("Comment", back_populates="post", cascade="all, delete-orphan")
    likes = relationship("PostLike", back_populates="post", cascade="all, delete-orphan")


# ── 评论 ──
class Comment(Base):
    __tablename__ = "comments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    post_id = Column(Integer, ForeignKey("posts.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.now)

    post = relationship("Post", back_populates="comments")
    user = relationship("User", back_populates="comments")


# ── 点赞 ──
class PostLike(Base):
    __tablename__ = "post_likes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    post_id = Column(Integer, ForeignKey("posts.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    __table_args__ = (
        UniqueConstraint("post_id", "user_id", name="uq_post_user_like"),
    )

    post = relationship("Post", back_populates="likes")


# ── 新闻资讯 ──
class News(Base):
    __tablename__ = "news"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(256), nullable=False)
    content = Column(Text, default="")
    cover_image = Column(String(512), default="")
    author = Column(String(64), default="管理员")
    is_published = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)
