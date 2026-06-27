import logging, tempfile, os, threading, traceback
logger = logging.getLogger(__name__)

_ocr = None
_ocr_lock = threading.Lock()
_ocr_status = "not_started"
_ocr_error = ""
_mock_mode = True

def get_status():
    return {"status": _ocr_status, "error": _ocr_error}

def init_ocr_background():
    global _ocr, _ocr_status, _ocr_error, _mock_mode
    try:
        from paddleocr import PaddleOCR
        ocr = PaddleOCR(use_textline_orientation=True, lang="ch")
        _ocr = ocr
        _mock_mode = False
        _ocr_status = "ready"
        logger.info("PaddleOCR initialized")
    except Exception as e:
        _ocr = None
        _mock_mode = True
        _ocr_status = "ready"
        _ocr_error = str(e)
        logger.warning(f"PaddleOCR unavailable, using mock mode: {e}")

def get_ocr():
    global _ocr
    if _ocr is not None:
        return _ocr
    return None

async def ocr_image(image_bytes: bytes) -> str:
    ocr = get_ocr()
    if ocr is None or _mock_mode:
        raise RuntimeError("OCR_UNAVAILABLE")
    tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
    tmp.write(image_bytes)
    tmp.close()
    try:
        result = ocr.ocr(tmp.name)
        texts = []
        if result and result[0]:
            for line in result[0]:
                texts.append(line[1][0])
        return "\n".join(texts) if texts else ""
    except Exception as e:
        logger.error(f"OCR inference error: {e}")
        raise RuntimeError(f"OCR_INFERENCE_ERROR: {e}")
    finally:
        try:
            os.unlink(tmp.name)
        except:
            pass
