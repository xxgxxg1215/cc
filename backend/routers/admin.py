"""
/admin — Web 管理后台（Jinja2 页面 + API）
"""
import json
import uuid
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, Form, Query, File, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, or_

from database import get_db
from models import User, RecognitionHistory, Encyclopedia, Post, Comment, News
from config import ADMIN_USERNAME, ADMIN_PASSWORD

router = APIRouter(prefix="/admin", tags=["管理后台"])

templates = Jinja2Templates(directory="templates")


# ── 简单的 session 管理 ──
_admin_sessions = set()


def check_admin(request: Request):
    token = request.cookies.get("admin_token", "")
    if token not in _admin_sessions:
        raise HTTPException(status_code=302, headers={"Location": "/admin/login"})


# ── 登录 ──

@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("admin_login.html", {"request": request, "error": ""})


@router.post("/login")
async def do_login(request: Request, username: str = Form(...), password: str = Form(...)):
    if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
        import uuid
        token = uuid.uuid4().hex
        _admin_sessions.add(token)
        response = RedirectResponse(url="/admin/dashboard", status_code=302)
        response.set_cookie("admin_token", token, max_age=86400)
        return response
    return templates.TemplateResponse(
        "admin_login.html", {"request": request, "error": "用户名或密码错误"}
    )


@router.get("/logout")
async def logout(request: Request):
    token = request.cookies.get("admin_token", "")
    _admin_sessions.discard(token)
    response = RedirectResponse(url="/admin/login", status_code=302)
    response.delete_cookie("admin_token")
    return response


# ── 数据大盘 ──

@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request, db: Session = Depends(get_db)):
    check_admin(request)

    user_count = db.query(func.count(User.id)).scalar()
    history_count = db.query(func.count(RecognitionHistory.id)).scalar()
    post_count = db.query(func.count(Post.id)).scalar()
    news_count = db.query(func.count(News.id)).scalar()
    enc_count = db.query(func.count(Encyclopedia.id)).scalar()

    # 健康 vs 病害比例
    healthy_count = db.query(func.count(RecognitionHistory.id)).filter(
        RecognitionHistory.is_healthy == True
    ).scalar()
    disease_count = history_count - healthy_count

    # 最近 7 天每日识别量
    today = datetime.now().date()
    daily_counts = []
    daily_labels = []
    for i in range(6, -1, -1):
        d = today - timedelta(days=i)
        cnt = (
            db.query(func.count(RecognitionHistory.id))
            .filter(func.date(RecognitionHistory.created_at) == d)
            .scalar()
        )
        daily_labels.append(d.strftime("%m-%d"))
        daily_counts.append(cnt or 0)

    # 病害 Top 10
    disease_stats = (
        db.query(RecognitionHistory.prediction, func.count(RecognitionHistory.id).label("cnt"))
        .filter(RecognitionHistory.is_healthy == False)
        .group_by(RecognitionHistory.prediction)
        .order_by(desc("cnt"))
        .limit(10)
        .all()
    )
    disease_names = [r[0] for r in disease_stats]
    disease_counts_list = [r[1] for r in disease_stats]

    # 最近5条识别记录
    recent_records = (
        db.query(RecognitionHistory)
        .order_by(desc(RecognitionHistory.created_at))
        .limit(5)
        .all()
    )

    return templates.TemplateResponse("admin_dashboard.html", {
        "request": request,
        "user_count": user_count,
        "history_count": history_count,
        "post_count": post_count,
        "news_count": news_count,
        "enc_count": enc_count,
        "healthy_count": healthy_count,
        "disease_count": disease_count,
        "daily_labels": json.dumps(daily_labels, ensure_ascii=False),
        "daily_counts": json.dumps(daily_counts),
        "disease_names": json.dumps(disease_names, ensure_ascii=False),
        "disease_counts": json.dumps(disease_counts_list),
        "recent_records": recent_records,
    })


# ── 用户管理 ──

@router.get("/users", response_class=HTMLResponse)
async def user_list(
    request: Request,
    page: int = 1,
    keyword: str = "",
    db: Session = Depends(get_db),
):
    check_admin(request)
    page_size = 20
    query = db.query(User)
    if keyword:
        query = query.filter(or_(
            User.nickname.contains(keyword),
            User.openid.contains(keyword),
        ))
    total = query.count()
    users = (
        query.order_by(desc(User.created_at))
        .offset((page - 1) * page_size).limit(page_size).all()
    )
    return templates.TemplateResponse("admin_users.html", {
        "request": request,
        "users": users,
        "total": total,
        "page": page,
        "keyword": keyword,
        "total_pages": max(1, (total + page_size - 1) // page_size),
    })


@router.post("/users/role/{user_id}")
async def change_role(
    user_id: int, request: Request,
    role: str = Form(...),
    db: Session = Depends(get_db),
):
    check_admin(request)
    user = db.query(User).filter(User.id == user_id).first()
    if user:
        user.role = role
        db.commit()
    return RedirectResponse(url="/admin/users", status_code=302)


# ── 识别记录管理 ──

@router.get("/history", response_class=HTMLResponse)
async def history_list(
    request: Request,
    page: int = 1,
    keyword: str = "",
    db: Session = Depends(get_db),
):
    check_admin(request)
    page_size = 20
    base = str(request.base_url).rstrip("/")
    query = db.query(RecognitionHistory)
    if keyword:
        query = query.filter(RecognitionHistory.prediction.contains(keyword))
    total = query.count()
    records = (
        query.order_by(desc(RecognitionHistory.created_at))
        .offset((page - 1) * page_size).limit(page_size).all()
    )
    # 拼接完整图片 URL
    for r in records:
        r.full_image_url = base + r.image_url if r.image_url else ""
    return templates.TemplateResponse("admin_history.html", {
        "request": request,
        "records": records,
        "total": total,
        "page": page,
        "keyword": keyword,
        "total_pages": max(1, (total + page_size - 1) // page_size),
    })


@router.post("/history/delete/{record_id}")
async def history_delete(record_id: int, request: Request, db: Session = Depends(get_db)):
    check_admin(request)
    db.query(RecognitionHistory).filter(RecognitionHistory.id == record_id).delete()
    db.commit()
    return RedirectResponse(url="/admin/history", status_code=302)


# ── 新闻管理 ──

@router.get("/news", response_class=HTMLResponse)
async def news_list(request: Request, page: int = 1, db: Session = Depends(get_db)):
    check_admin(request)
    page_size = 20
    total = db.query(func.count(News.id)).scalar()
    items = (
        db.query(News)
        .order_by(desc(News.created_at))
        .offset((page - 1) * page_size).limit(page_size).all()
    )
    return templates.TemplateResponse("admin_news.html", {
        "request": request,
        "news_list": items,
        "total": total,
        "page": page,
        "total_pages": max(1, (total + page_size - 1) // page_size),
    })


@router.post("/news/create")
async def news_create(
    request: Request,
    title: str = Form(...),
    content: str = Form(""),
    cover_image: UploadFile = File(None),
    author: str = Form("管理员"),
    db: Session = Depends(get_db),
):
    check_admin(request)
    cover_url = ""
    if cover_image and cover_image.filename:
        import os
        from config import UPLOAD_DIR
        ext = os.path.splitext(cover_image.filename)[1] or ".jpg"
        fname = uuid.uuid4().hex + ext
        path = os.path.join(UPLOAD_DIR, fname)
        file_bytes = await cover_image.read()
        with open(path, "wb") as f:
            f.write(file_bytes)
        cover_url = f"/uploads/{fname}"
    news = News(title=title, content=content, cover_image=cover_url, author=author)
    db.add(news)
    db.commit()
    return RedirectResponse(url="/admin/news", status_code=302)


@router.post("/news/delete/{news_id}")
async def news_delete(news_id: int, request: Request, db: Session = Depends(get_db)):
    check_admin(request)
    db.query(News).filter(News.id == news_id).delete()
    db.commit()
    return RedirectResponse(url="/admin/news", status_code=302)


@router.post("/news/toggle/{news_id}")
async def news_toggle(news_id: int, request: Request, db: Session = Depends(get_db)):
    check_admin(request)
    news = db.query(News).filter(News.id == news_id).first()
    if news:
        news.is_published = not news.is_published
        db.commit()
    return RedirectResponse(url="/admin/news", status_code=302)


# ── 社区管理 ──

@router.get("/community", response_class=HTMLResponse)
async def community_list(request: Request, page: int = 1, db: Session = Depends(get_db)):
    check_admin(request)
    page_size = 20
    total = db.query(func.count(Post.id)).scalar()
    posts = (
        db.query(Post)
        .order_by(desc(Post.created_at))
        .offset((page - 1) * page_size).limit(page_size).all()
    )
    return templates.TemplateResponse("admin_community.html", {
        "request": request,
        "posts": posts,
        "total": total,
        "page": page,
        "total_pages": max(1, (total + page_size - 1) // page_size),
    })


@router.post("/community/delete/{post_id}")
async def community_delete(post_id: int, request: Request, db: Session = Depends(get_db)):
    check_admin(request)
    # 先删评论再删帖子
    db.query(Comment).filter(Comment.post_id == post_id).delete()
    db.query(Post).filter(Post.id == post_id).delete()
    db.commit()
    return RedirectResponse(url="/admin/community", status_code=302)


# ── 百科管理 ──

@router.get("/encyclopedia", response_class=HTMLResponse)
async def encyclopedia_list(
    request: Request,
    page: int = 1,
    keyword: str = "",
    crop: str = "",
    db: Session = Depends(get_db),
):
    check_admin(request)
    page_size = 20
    query = db.query(Encyclopedia)
    if keyword:
        query = query.filter(or_(
            Encyclopedia.disease_name.contains(keyword),
            Encyclopedia.disease_en.contains(keyword),
        ))
    if crop:
        query = query.filter(Encyclopedia.crop_name == crop)
        
    total = query.count()
    items = (
        query.order_by(Encyclopedia.crop_name, Encyclopedia.id)
        .offset((page - 1) * page_size).limit(page_size).all()
    )

    # 获取所有作物名用于筛选
    crops = db.query(Encyclopedia.crop_name).distinct().order_by(Encyclopedia.crop_name).all()
    crop_list = [c[0] for c in crops]

    return templates.TemplateResponse("admin_encyclopedia.html", {
        "request": request,
        "items": items,
        "keyword": keyword,
        "current_crop": crop,
        "crop_list": crop_list,
        "total": total,
        "page": page,
        "total_pages": max(1, (total + page_size - 1) // page_size),
    })


@router.post("/encyclopedia/delete/{item_id}")
async def encyclopedia_delete(item_id: int, request: Request, db: Session = Depends(get_db)):
    check_admin(request)
    db.query(Encyclopedia).filter(Encyclopedia.id == item_id).delete()
    db.commit()
    return RedirectResponse(url="/admin/encyclopedia", status_code=302)
