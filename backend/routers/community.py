"""
/api/community — 社区互动（帖子 / 评论 / 点赞）
"""
import json
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc

from database import get_db
from models import Post, Comment, PostLike, User
from routers.user import parse_token

router = APIRouter(prefix="/api/community", tags=["社区"])


# ── 请求体 ──

class PostCreateRequest(BaseModel):
    title: str
    content: str = ""
    image_urls: list[str] = []


class CommentCreateRequest(BaseModel):
    content: str


# ── 帖子接口 ──

@router.get("/posts")
async def list_posts(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    db: Session = Depends(get_db),
):
    """帖子列表（公开）"""
    query = db.query(Post).options(joinedload(Post.user)).order_by(desc(Post.created_at))
    total = query.count()
    posts = query.offset((page - 1) * page_size).limit(page_size).all()
    return {
        "total": total,
        "page": page,
        "list": [
            {
                "id": p.id,
                "title": p.title,
                "content": p.content[:100] + "…" if len(p.content) > 100 else p.content,
                "image_urls": json.loads(p.image_urls) if p.image_urls else [],
                "like_count": p.like_count,
                "comment_count": p.comment_count,
                "created_at": p.created_at.strftime("%Y-%m-%d %H:%M"),
                "user": {
                    "id": p.user.id,
                    "nickname": p.user.nickname,
                    "avatar_url": p.user.avatar_url,
                    "role": p.user.role,
                },
            }
            for p in posts
        ],
    }


@router.get("/posts/{post_id}")
async def get_post(post_id: int, db: Session = Depends(get_db)):
    """帖子详情 + 评论列表"""
    post = (
        db.query(Post)
        .options(joinedload(Post.user), joinedload(Post.comments).joinedload(Comment.user))
        .filter(Post.id == post_id)
        .first()
    )
    if not post:
        raise HTTPException(status_code=404, detail="帖子不存在")
    return {
        "id": post.id,
        "title": post.title,
        "content": post.content,
        "image_urls": json.loads(post.image_urls) if post.image_urls else [],
        "like_count": post.like_count,
        "comment_count": post.comment_count,
        "created_at": post.created_at.strftime("%Y-%m-%d %H:%M"),
        "user": {
            "id": post.user.id,
            "nickname": post.user.nickname,
            "avatar_url": post.user.avatar_url,
            "role": post.user.role,
        },
        "comments": [
            {
                "id": c.id,
                "content": c.content,
                "created_at": c.created_at.strftime("%Y-%m-%d %H:%M"),
                "user": {
                    "id": c.user.id,
                    "nickname": c.user.nickname,
                    "avatar_url": c.user.avatar_url,
                    "role": c.user.role,
                },
            }
            for c in sorted(post.comments, key=lambda x: x.created_at)
        ],
    }


@router.post("/posts")
async def create_post(req: PostCreateRequest, token: str = "", db: Session = Depends(get_db)):
    """发帖（需登录）"""
    user_id = parse_token(token)
    post = Post(
        user_id=user_id,
        title=req.title,
        content=req.content,
        image_urls=json.dumps(req.image_urls, ensure_ascii=False) if req.image_urls else "",
    )
    db.add(post)
    db.commit()
    db.refresh(post)
    return {"message": "发布成功", "post_id": post.id}


@router.delete("/posts/{post_id}")
async def delete_post(post_id: int, token: str = "", db: Session = Depends(get_db)):
    """删帖（仅限本人或管理员）"""
    user_id = parse_token(token)
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="帖子不存在")
    user = db.query(User).filter(User.id == user_id).first()
    if post.user_id != user_id and (not user or user.role != "admin"):
        raise HTTPException(status_code=403, detail="无权限")
    db.delete(post)
    db.commit()
    return {"message": "删除成功"}


# ── 评论 ──

@router.post("/posts/{post_id}/comments")
async def create_comment(
    post_id: int,
    req: CommentCreateRequest,
    token: str = "",
    db: Session = Depends(get_db),
):
    """发表评论"""
    user_id = parse_token(token)
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="帖子不存在")
    comment = Comment(post_id=post_id, user_id=user_id, content=req.content)
    db.add(comment)
    post.comment_count += 1
    db.commit()
    return {"message": "评论成功"}


# ── 点赞 ──

@router.post("/posts/{post_id}/like")
async def toggle_like(post_id: int, token: str = "", db: Session = Depends(get_db)):
    """点赞 / 取消点赞"""
    user_id = parse_token(token)
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="帖子不存在")
    existing = (
        db.query(PostLike)
        .filter(PostLike.post_id == post_id, PostLike.user_id == user_id)
        .first()
    )
    if existing:
        db.delete(existing)
        post.like_count = max(0, post.like_count - 1)
        db.commit()
        return {"message": "取消点赞", "liked": False, "like_count": post.like_count}
    else:
        db.add(PostLike(post_id=post_id, user_id=user_id))
        post.like_count += 1
        db.commit()
        return {"message": "点赞成功", "liked": True, "like_count": post.like_count}
