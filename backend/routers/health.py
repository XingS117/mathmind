from fastapi import APIRouter
from backend.services.ocr_service import get_status
router = APIRouter(tags=["health"])

@router.get("/health/ocr")
def ocr_health():
    s = get_status()
    msg = {"not_started": "OCR 未启动，将在首次请求时初始化（约需30-120秒）",
           "initializing": "OCR 正在下载模型，请稍候（约需30-120秒）",
           "ready": "OCR 就绪",
           "failed": f"OCR 初始化失败：{s.get('error', '')}"}
    return {"status": s["status"], "message": msg.get(s["status"], "")}