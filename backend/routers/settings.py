import logging
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session as DBSession
from backend.database import get_db
from backend.services.auth_service import get_user_id
from backend.models.settings import UserSettings

logger = logging.getLogger(__name__)
router = APIRouter(tags=["settings"])

class ModelConfig(BaseModel):
    model_provider: str = "mock"
    model_name: str = "mock"
    api_key: str = ""
    base_url: str = ""

PROVIDER_MODELS = {
    "mock": {"models": ["mock"], "default_base_url": ""},
    "deepseek": {"models": ["deepseek-chat", "deepseek-reasoner"], "default_base_url": "https://api.deepseek.com/v1"},
    "openai": {"models": ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-4"], "default_base_url": "https://api.openai.com/v1"},
    "gemini": {"models": ["gemini-2.0-flash", "gemini-2.0-pro"], "default_base_url": "https://generativelanguage.googleapis.com/v1beta"},
    "qwen": {"models": ["qwen-plus", "qwen-turbo", "qwen-max"], "default_base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1"},
    "moonshot": {"models": ["moonshot-v1-8k", "moonshot-v1-32k", "moonshot-v1-128k"], "default_base_url": "https://api.moonshot.cn/v1"},
    "tencent": {"models": ["hunyuan-large", "hunyuan-pro", "hunyuan-standard", "hunyuan-lite"], "default_base_url": "https://api.hunyuan.cloud.tencent.com/v1"},
    "minimax": {"models": ["MiniMax-M3", "MiniMax-M2.7", "MiniMax-M2.7-highspeed", "MiniMax-M2.5", "MiniMax-M2.5-highspeed", "MiniMax-M2.1", "MiniMax-M2.1-highspeed", "MiniMax-M2"], "default_base_url": "https://api.minimax.chat/v1"},
}

@router.get("/settings/providers")
def get_providers():
    return {
        "providers": [
            {"id": k, "name": {"mock": "Mock模式（本地测试）", "deepseek": "DeepSeek", "openai": "OpenAI", "gemini": "Google Gemini", "qwen": "阿里通义千问", "moonshot": "月之暗面 Moonshot", "tencent": "腾讯混元", "minimax": "MiniMax"}.get(k, k),
             "models": v["models"], "default_base_url": v["default_base_url"]}
            for k, v in PROVIDER_MODELS.items()
        ]
    }

@router.get("/settings/models", response_model=ModelConfig)
def get_model_config(request: Request, db: DBSession = Depends(get_db)):
    uid = get_user_id(request)
    s = db.query(UserSettings).filter(UserSettings.user_id == uid).first()
    if not s:
        return ModelConfig()
    return ModelConfig(model_provider=s.model_provider, model_name=s.model_name, api_key=s.api_key or "", base_url=s.base_url or "")

@router.put("/settings/models", response_model=ModelConfig)
def update_model_config(config: ModelConfig, request: Request, db: DBSession = Depends(get_db)):
    uid = get_user_id(request)
    s = db.query(UserSettings).filter(UserSettings.user_id == uid).first()
    if not s:
        s = UserSettings(user_id=uid)
        db.add(s)
    s.model_provider = config.model_provider
    s.model_name = config.model_name
    s.api_key = config.api_key
    s.base_url = config.base_url
    db.commit()
    logger.info(f"Model config updated: {config.model_provider}/{config.model_name}")
    return config

@router.post("/settings/models/test")
def test_connection(config: ModelConfig, request: Request, db: DBSession = Depends(get_db)):
    if config.model_provider == "mock":
        return {"status": "ok", "message": "Mock 模式无需连接"}
    if not config.api_key:
        raise HTTPException(400, "请填写 API Key")
    try:
        import httpx
        headers = {"Authorization": f"Bearer {config.api_key}", "Content-Type": "application/json"}
        base = config.base_url or PROVIDER_MODELS.get(config.model_provider, {}).get("default_base_url", "")
        if not base:
            raise HTTPException(400, "请填写 API 地址")
        r = httpx.post(f"{base}/chat/completions", json={
            "model": config.model_name,
            "messages": [{"role": "user", "content": "Hi"}],
            "max_tokens": 5
        }, headers=headers, timeout=10)
        if r.status_code == 200:
            return {"status": "ok", "message": f"连接成功！模型响应正常"}
        else:
            return {"status": "error", "message": f"API 返回错误: {r.status_code}"}
    except Exception as e:
        return {"status": "error", "message": f"连接失败: {str(e)[:100]}"}