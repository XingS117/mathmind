import logging
from urllib.parse import urlparse
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


class ModelConfigResponse(BaseModel):
    model_provider: str = "mock"
    model_name: str = "mock"
    api_key: str = ""
    api_key_configured: bool = False
    base_url: str = ""

PROVIDER_MODELS = {
    "mock": {"models": ["mock"], "default_base_url": ""},
    "deepseek": {"models": ["deepseek-v4-pro", "deepseek-v4-flash", "deepseek-chat"], "default_base_url": "https://api.deepseek.com/v1"},
    "openai": {"models": ["gpt-5.6-sol", "gpt-5.6-terra", "gpt-5.6-luna"], "default_base_url": "https://api.openai.com/v1"},
    "gemini": {"models": ["gemini-3.5", "gemini-3.5-flash", "gemini-2.5-pro"], "default_base_url": "https://generativelanguage.googleapis.com/v1beta"},
    "qwen": {"models": ["qwen3.7-max", "qwen3.6-plus", "qwen3.6-flash"], "default_base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1"},
    "moonshot": {"models": ["kimi-latest", "kimi-k2.7-code", "moonshot-v1-128k"], "default_base_url": "https://api.moonshot.cn/v1"},
    "tencent": {"models": ["hunyuan-large", "hunyuan-pro", "hunyuan-standard", "hunyuan-lite"], "default_base_url": "https://api.hunyuan.cloud.tencent.com/v1"},
    "minimax": {"models": ["MiniMax-M3", "MiniMax-M2.7", "MiniMax-M2.7-highspeed", "MiniMax-M2.5", "MiniMax-M2.5-highspeed", "MiniMax-M2.1", "MiniMax-M2.1-highspeed", "MiniMax-M2"], "default_base_url": "https://api.minimaxi.com/v1"},
}


def _require_user(request: Request, db: DBSession) -> str:
    uid = get_user_id(request, db=db)
    if uid == "u_default":
        raise HTTPException(401, "请先登录")
    return uid


def _safe_base_url(config: ModelConfig) -> str:
    provider = PROVIDER_MODELS.get(config.model_provider)
    if provider is None:
        raise HTTPException(400, "不支持的模型提供商")
    base_url = config.base_url.strip() or provider["default_base_url"]
    if config.model_provider == "mock":
        return ""
    parsed = urlparse(base_url)
    allowed = urlparse(provider["default_base_url"])
    if parsed.scheme != "https" or parsed.hostname != allowed.hostname:
        raise HTTPException(400, "API 地址必须为该提供商的 HTTPS 官方地址")
    return base_url.rstrip("/")

@router.get("/settings/providers")
def get_providers():
    return {
        "providers": [
            {"id": k, "name": {"mock": "Mock模式（本地测试）", "deepseek": "DeepSeek", "openai": "OpenAI", "gemini": "Google Gemini", "qwen": "阿里通义千问", "moonshot": "月之暗面 Moonshot", "tencent": "腾讯混元", "minimax": "MiniMax"}.get(k, k),
             "models": v["models"], "default_base_url": v["default_base_url"]}
            for k, v in PROVIDER_MODELS.items()
        ]
    }

@router.get("/settings/models", response_model=ModelConfigResponse)
def get_model_config(request: Request, db: DBSession = Depends(get_db)):
    uid = _require_user(request, db)
    s = db.query(UserSettings).filter(UserSettings.user_id == uid).first()
    if not s:
        return ModelConfigResponse()
    return ModelConfigResponse(model_provider=s.model_provider, model_name=s.model_name,
                               api_key_configured=bool(s.api_key), base_url=s.base_url or "")

@router.put("/settings/models", response_model=ModelConfigResponse)
def update_model_config(config: ModelConfig, request: Request, db: DBSession = Depends(get_db)):
    uid = _require_user(request, db)
    base_url = _safe_base_url(config)
    s = db.query(UserSettings).filter(UserSettings.user_id == uid).first()
    if not s:
        s = UserSettings(user_id=uid)
        db.add(s)
    s.model_provider = config.model_provider
    s.model_name = config.model_name
    if config.api_key:
        s.api_key = config.api_key
    s.base_url = base_url
    db.commit()
    logger.info(f"Model config updated: {config.model_provider}/{config.model_name}")
    return ModelConfigResponse(model_provider=s.model_provider, model_name=s.model_name,
                               api_key_configured=bool(s.api_key), base_url=s.base_url)

@router.post("/settings/models/test")
def test_connection(config: ModelConfig, request: Request, db: DBSession = Depends(get_db)):
    _require_user(request, db)
    if config.model_provider == "mock":
        return {"status": "ok", "message": "Mock 模式无需连接"}
    if not config.api_key:
        raise HTTPException(400, "请填写 API Key")
    base = _safe_base_url(config)
    try:
        import httpx
        headers = {"Authorization": f"Bearer {config.api_key}", "Content-Type": "application/json"}
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
