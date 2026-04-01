"""
AI 聊天助手 - 回答农业相关问题（使用讯飞星火免费API）
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
import httpx
from sqlalchemy.orm import Session
import json

from database import get_db
from models import User
from config import XUNFEI_APPID, XUNFEI_SECRET, XUNFEI_TOKEN
from disease_info import DISEASE_INFO

router = APIRouter(prefix="/chat", tags=["聊天助手"])

# 农业知识背景
AGRICULTURE_SYSTEM_PROMPT = """
你是一位专业的农业顾问助手。你的职责是：
1. 只回答与农业、种植、病害防治相关的问题
2. 基于以下病害知识库提供准确的建议
3. 如果用户问非农业相关的问题，礼貌地拒绝并引导回农业话题

已知病害信息：
"""

# 构建病害知识库文本
DISEASE_KNOWLEDGE = AGRICULTURE_SYSTEM_PROMPT
for disease_name, disease_info in DISEASE_INFO.items():
    DISEASE_KNOWLEDGE += f"\n{disease_name}: {disease_info.get('description', '')}"


class ChatRequest(BaseModel):
    message: str
    user_id: int = None


class ChatResponse(BaseModel):
    answer: str
    is_agriculture: bool


async def get_xunfei_token():
    """获取讯飞星火的访问令牌"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://aip.baidubce.com/oauth/2.0/token",
                params={
                    "grant_type": "client_credentials",
                    "client_id": XUNFEI_APPID,
                    "client_secret": XUNFEI_SECRET
                }
            )
            data = response.json()
            return data.get("access_token")
    except Exception:
        return None


@router.post("/message", response_model=ChatResponse)
async def chat_message(request: ChatRequest, db: Session = Depends(get_db)):
    """
    聊天接口 - 回答农业问题（使用讯飞星火）
    
    参数：
    - message: 用户输入的问题
    - user_id: 用户 ID（可选）
    
    返回：
    - answer: AI 的回答
    - is_agriculture: 是否识别为农业问题
    """
    
    if not XUNFEI_APPID or not XUNFEI_SECRET:
        raise HTTPException(status_code=500, detail="讯飞 API 未配置")
    
    if not request.message or len(request.message.strip()) == 0:
        raise HTTPException(status_code=400, detail="请输入有效的问题")
    
    try:
        # 获取百度文心的 access token
        async with httpx.AsyncClient() as client:
            # 先获取 token
            token_response = await client.post(
                "https://aip.baidubce.com/oauth/2.0/token",
                params={
                    "grant_type": "client_credentials",
                    "client_id": XUNFEI_APPID,
                    "client_secret": XUNFEI_SECRET
                }
            )
            token_data = token_response.json()
            access_token = token_data.get("access_token")
            
            if not access_token:
                raise Exception("无法获取访问令牌")
            
            # 调用百度文心一言 API
            chat_response = await client.post(
                f"https://aip.baidubce.com/rpc/2.0/ai_custom/v1/wenxinworkshop/chat/ernie-3.5-128k?access_token={access_token}",
                json={
                    "messages": [
                        {
                            "role": "user",
                            "content": f"你是一位农业顾问。{request.message}\n\n农业知识库：{DISEASE_KNOWLEDGE}\n\n请检查这是否是农业问题。如果是，提供专业建议。如果不是，说'这不是农业问题，我只能回答农业相关的问题'。"
                        }
                    ]
                },
                timeout=30
            )
            
            response_data = chat_response.json()
            
            if "result" in response_data:
                answer = response_data["result"]
            elif "error_msg" in response_data:
                raise Exception(f"API 错误: {response_data['error_msg']}")
            else:
                raise Exception("无效的 API 响应")
            
            is_agriculture = "不是农业问题" not in answer
            
            return ChatResponse(
                answer=answer,
                is_agriculture=is_agriculture
            )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI 服务出错: {str(e)}")


@router.get("/health")
async def chat_health():
    """检查聊天服务是否可用"""
    return {
        "status": "ok" if XUNFEI_APPID else "error",
        "message": "聊天助手已就绪" if XUNFEI_APPID else "讯飞 API 未配置"
    }
