import json, logging, time
import httpx

from backend.database import SessionLocal
from backend.services.operations_service import record_runtime_event

logger = logging.getLogger(__name__)

DEEPSEEK_API_KEY = ""
DEEPSEEK_BASE_URL = "https://api.deepseek.com/v1"
LLM_MOCK = True

async def call_llm(prompt: str, system: str = "") -> str:
    started = time.monotonic()
    outcome = "success"
    error_code = None
    try:
        if LLM_MOCK:
            return ""
        headers = {"Authorization": f"Bearer {DEEPSEEK_API_KEY}", "Content-Type": "application/json"}
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(f"{DEEPSEEK_BASE_URL}/chat/completions", json={
                "model": "deepseek-chat", "messages": messages, "temperature": 0.1, "max_tokens": 4096
            }, headers=headers)
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"]
    except Exception as e:
        outcome = "error"
        error_code = type(e).__name__
        logger.error("LLM external request failed (%s)", type(e).__name__)
        return ""
    finally:
        _record_runtime("deepseek", "deepseek-chat", outcome, started, error_code)

async def call_llm_with_config(prompt: str, config: dict, system: str = "") -> str:
    provider = config.get("model_provider", "mock")
    model = config.get("model_name", "mock")
    started = time.monotonic()
    outcome = "success"
    error_code = None
    try:
        api_key = config.get("api_key", "")
        base_url = config.get("base_url", "")
        if provider == "mock" or not api_key:
            return ""
        defaults = {
            "deepseek": "https://api.deepseek.com/v1", "openai": "https://api.openai.com/v1",
            "gemini": "https://generativelanguage.googleapis.com/v1beta", "qwen": "https://dashscope.aliyuncs.com/compatible-mode/v1",
            "moonshot": "https://api.moonshot.cn/v1", "tencent": "https://api.hunyuan.cloud.tencent.com/v1",
            "minimax": "https://api.minimaxi.com/v1",
        }
        if not base_url:
            base_url = defaults.get(provider, "")
        if not base_url:
            return ""
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(f"{base_url}/chat/completions", json={
                "model": model, "messages": messages, "temperature": 0.1, "max_tokens": 4096
            }, headers=headers)
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"]
    except Exception as e:
        outcome = "error"
        error_code = type(e).__name__
        logger.error("LLM external request failed (%s)", type(e).__name__)
        return ""
    finally:
        _record_runtime(provider, model, outcome, started, error_code)


def _record_runtime(provider: str, model_name: str, outcome: str, started: float, error_code: str | None) -> None:
    db = None
    try:
        db = SessionLocal()
        record_runtime_event(
            db, feature="llm", engine_kind="text", provider=provider, model_name=model_name,
            outcome=outcome, duration_ms=round((time.monotonic() - started) * 1000), error_code=error_code,
        )
    except Exception:
        logger.warning("Failed to record LLM runtime event", exc_info=True)
    finally:
        if db is not None:
            try:
                db.close()
            except Exception:
                logger.warning("Failed to close LLM telemetry session", exc_info=True)
