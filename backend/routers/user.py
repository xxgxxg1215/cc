"""
/api/user — 用户系统（微信登录、个人信息）
"""
import time
import httpx
import jwt

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from models import User
from config import WX_APPID, WX_SECRET, SECRET_KEY, JWT_ALGORITHM, JWT_EXPIRE_HOURS

router = APIRouter(prefix="/api/user", tags=["用户"])


# ── Pydantic 模型 ──

class WxLoginRequest(BaseModel):
    code: str
    nickname: str = "微信用户"
    avatar_url: str = ""


class UserUpdateRequest(BaseModel):
    nickname: str | None = None
    avatar_url: str | None = None


# ── 工具函数 ──

def create_token(user_id: int) -> str:
    payload = {
        "user_id": user_id,
        "exp": int(time.time()) + JWT_EXPIRE_HOURS * 3600,
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=JWT_ALGORITHM)


def parse_token(token: str) -> int:
    """解析 token 返回 user_id，失败抛异常"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return payload["user_id"]
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="登录已过期，请重新登录")
    except Exception:
        raise HTTPException(status_code=401, detail="无效的认证信息")


def get_current_user_id(token: str = "") -> int:
    """通用依赖 — 从 header 或 query 获取 user_id"""
    if not token:
        raise HTTPException(status_code=401, detail="未登录")
    return parse_token(token)


# ── 接口 ──

@router.post("/login")
async def wx_login(req: WxLoginRequest, db: Session = Depends(get_db)):
    """
    微信小程序登录
    1. 通过 code 换取 openid
    2. 如果用户不存在则自动注册
    3. 返回 JWT token
    """
    # 请求微信 code2session
    openid = ""
    if WX_APPID and WX_SECRET:
        url = (
            f"https://api.weixin.qq.com/sns/jscode2session"
            f"?appid={WX_APPID}&secret={WX_SECRET}"
            f"&js_code={req.code}&grant_type=authorization_code"
        )
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, timeout=10)
            data = resp.json()
            openid = data.get("openid", "")
            if not openid:
                raise HTTPException(status_code=400, detail="微信登录失败: " + data.get("errmsg", ""))
    else:
        # 开发模式：没有配置 appid 时，用 code 当 openid
        openid = req.code

    # 查找或创建用户
    user = db.query(User).filter(User.openid == openid).first()
    if not user:
        user = User(
            openid=openid,
            nickname=req.nickname,
            avatar_url=req.avatar_url,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    else:
        # 更新昵称和头像
        if req.nickname and req.nickname != "微信用户":
            user.nickname = req.nickname
        if req.avatar_url:
            user.avatar_url = req.avatar_url
        db.commit()

    token = create_token(user.id)

    return {
        "token": token,
        "user": {
            "id": user.id,
            "nickname": user.nickname,
            "avatar_url": user.avatar_url,
            "role": user.role,
        }
    }


@router.get("/profile")
async def get_profile(token: str = "", db: Session = Depends(get_db)):
    """获取用户个人信息"""
    user_id = parse_token(token)
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    return {
        "id": user.id,
        "nickname": user.nickname,
        "avatar_url": user.avatar_url,
        "role": user.role,
        "created_at": user.created_at.strftime("%Y-%m-%d"),
    }


@router.put("/profile")
async def update_profile(req: UserUpdateRequest, token: str = "", db: Session = Depends(get_db)):
    """更新用户信息"""
    user_id = parse_token(token)
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    if req.nickname is not None:
        user.nickname = req.nickname
    if req.avatar_url is not None:
        user.avatar_url = req.avatar_url
    db.commit()
    return {"message": "更新成功"}
