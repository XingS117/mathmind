import logging, base64, json
import httpx

logger = logging.getLogger(__name__)

# Providers that support vision/image input
VISION_PROVIDERS = {"openai", "gemini", "qwen"}

VISION_MODELS = {
    "openai": {"gpt-4o", "gpt-4o-mini", "gpt-4-turbo"},
    "gemini": {"gemini-2.0-flash", "gemini-2.0-pro"},
    "qwen": {"qwen-vl-plus", "qwen-vl-max", "qwen-plus", "qwen-max"},
}

OCR_PROMPT = """你是一个数学题OCR助手。请识别图片中的所有文字内容，包括：
1. 题目文本
2. 数学公式（用LaTeX格式，用$包裹）
3. 几何图形的文字标注

只输出识别到的文字内容，不要添加任何额外说明。
如果图片不包含有效文字，请输出：NO_TEXT_FOUND"""

async def ocr_with_vision_llm(image_bytes: bytes, config: dict) -> str:
    """Use a vision-capable LLM to extract text from an image."""
    provider = config.get("model_provider", "")
    api_key = config.get("api_key", "")
    model = config.get("model_name", "")
    base_url = config.get("base_url", "")
    
    if provider not in VISION_PROVIDERS or not api_key:
        return ""
    
    # Check if the model supports vision
    supported = VISION_MODELS.get(provider, set())
    if model not in supported and provider != "gemini":
        # Gemini models all support vision
        return ""
    
    # Convert image to base64
    image_b64 = base64.b64encode(image_bytes).decode("utf-8")
    
    try:
        if provider == "gemini":
            return await _call_gemini_vision(image_b64, api_key, model, base_url)
        else:
            return await _call_openai_vision(image_b64, api_key, model, base_url, provider)
    except Exception as e:
        logger.error("Vision LLM OCR request failed (%s)", type(e).__name__)
        return ""

async def _call_openai_vision(image_b64: str, api_key: str, model: str, base_url: str, provider: str) -> str:
    """Call OpenAI-compatible vision API."""
    if not base_url:
        defaults = {
            "openai": "https://api.openai.com/v1",
            "qwen": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        }
        base_url = defaults.get(provider, "")
    
    if not base_url:
        return ""
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    content = [
        {"type": "text", "text": OCR_PROMPT},
        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_b64}"}}
    ]
    
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": content}],
        "max_tokens": 2048,
        "temperature": 0.1
    }
    
    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(
            f"{base_url}/chat/completions",
            json=payload,
            headers=headers
        )
        resp.raise_for_status()
        result = resp.json()
        text = result["choices"][0]["message"]["content"].strip()
        if text == "NO_TEXT_FOUND":
            return ""
        return text

async def _call_gemini_vision(image_b64: str, api_key: str, model: str, base_url: str) -> str:
    """Call Google Gemini vision API."""
    if not base_url:
        base_url = "https://generativelanguage.googleapis.com/v1beta"
    
    parts = [
        {"text": OCR_PROMPT},
        {"inlineData": {"mimeType": "image/png", "data": image_b64}}
    ]
    
    payload = {"contents": [{"parts": parts}]}
    url = f"{base_url}/models/{model}:generateContent?key={api_key}"
    
    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(url, json=payload, headers={"Content-Type": "application/json"})
        resp.raise_for_status()
        result = resp.json()
        candidates = result.get("candidates", [])
        if candidates:
            text_parts = candidates[0].get("content", {}).get("parts", [])
            text = "".join(p.get("text", "") for p in text_parts).strip()
            if text == "NO_TEXT_FOUND":
                return ""
            return text
        return ""
