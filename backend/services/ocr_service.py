"""PaddleOCR wrapper for MathMind.

Handles PaddleOCR 3.x on Windows where the default OneDNN + PIR executor path
raises ``ConvertPirAttribute2RuntimeAttribute not support`` on ``.ocr()``.

Strategy:
1. Initialise PaddleOCR with OneDNN disabled to avoid the incompatible kernel.
   Fall back to a plain constructor if the flag is rejected by an older build.
2. Prefer the new ``.predict()`` inference entry point exposed by PaddleOCR 3.x.
   Only fall back to legacy ``.ocr()`` when ``.predict()`` is unavailable.
3. Parse both the 3.x dict-shape result (``rec_texts``/``rec_scores``) and the
   legacy ``[[box, (text, score)], ...]`` shape defensively so an unexpected
   structure never crashes the request handler.
"""

import logging
import os
import tempfile
import threading
from typing import Any

logger = logging.getLogger(__name__)

_ocr = None
_ocr_lock = threading.Lock()
_ocr_status = "not_started"
_ocr_error = ""
_mock_mode = True


def get_status():
    return {"status": _ocr_status, "error": _ocr_error}


def _try_construct(paddle_ocr_cls, **kwargs):
    """Try to construct PaddleOCR with the given kwargs, tolerating unknowns."""
    try:
        return paddle_ocr_cls(**kwargs), None
    except TypeError as exc:
        # Older / newer builds may not accept every kwarg; retry without
        # unsupported ones one at a time.
        return None, exc
    except Exception as exc:  # noqa: BLE001
        return None, exc


def _do_init():
    """Actually construct PaddleOCR. May take 30-120s on first cold start."""
    global _ocr, _ocr_status, _ocr_error, _mock_mode
    try:
        from paddleocr import PaddleOCR

        attempts = [
            # PaddleOCR 3.x accepts ``enable_mkldnn=False`` to disable OneDNN.
            {"use_textline_orientation": True, "lang": "ch", "enable_mkldnn": False},
            # Some 3.x releases only expose ``use_mkldnn``.
            {"use_textline_orientation": True, "lang": "ch", "use_mkldnn": False},
            # Last resort: default construction (may hit the PIR bug on inference).
            {"use_textline_orientation": True, "lang": "ch"},
        ]

        ocr = None
        last_exc = None
        for kwargs in attempts:
            candidate, exc = _try_construct(PaddleOCR, **kwargs)
            if candidate is not None:
                ocr = candidate
                logger.info(f"PaddleOCR initialized with {kwargs}")
                break
            last_exc = exc
            logger.warning(f"PaddleOCR init attempt failed for {kwargs}: {exc}")

        if ocr is None:
            raise last_exc if last_exc else RuntimeError("PaddleOCR init failed")

        _ocr = ocr
        _mock_mode = False
        _ocr_status = "ready"
    except Exception as e:  # noqa: BLE001
        _ocr = None
        _mock_mode = True
        _ocr_status = "failed"
        _ocr_error = str(e)
        logger.warning(f"PaddleOCR unavailable, using mock mode: {e}")


def init_ocr_background():
    """Kick off OCR initialisation on a daemon thread so app startup does
    not block for 1-2 minutes waiting on PaddleOCR model loading. Health
    endpoint reports ``initializing`` until ``_do_init`` finishes.
    """
    global _ocr_status
    with _ocr_lock:
        if _ocr_status in ("initializing", "ready"):
            return
        _ocr_status = "initializing"
    thread = threading.Thread(target=_do_init, name="paddleocr-init", daemon=True)
    thread.start()


def get_ocr():
    return _ocr


def _extract_texts(result: Any) -> list[str]:
    """Extract recognised text lines from a PaddleOCR ``predict``/``ocr`` result.

    Handles the two shapes we have observed in the wild:
    - 3.x ``predict``: ``[{"rec_texts": [...], "rec_scores": [...], ...}, ...]``
      or the same dict directly (not wrapped in a list).
    - Legacy ``ocr``: ``[[[box, (text, score)], ...]]`` per image.
    Anything else returns ``[]`` rather than raising.
    """
    if result is None:
        return []

    # 3.x predict may return an object with ``.json`` attribute pointing to a
    # dict with ``res``; unwrap when present.
    if hasattr(result, "json") and not isinstance(result, (list, tuple, dict, str)):
        try:
            result = result.json
        except Exception:  # noqa: BLE001
            pass
    if isinstance(result, dict) and "res" in result and isinstance(result["res"], (list, dict)):
        result = result["res"]

    items = result if isinstance(result, list) else [result]
    texts: list[str] = []
    for item in items:
        if item is None:
            continue
        # 3.x dict shape.
        if isinstance(item, dict):
            rec_texts = item.get("rec_texts")
            if isinstance(rec_texts, list):
                for t in rec_texts:
                    if isinstance(t, str) and t.strip():
                        texts.append(t)
                continue
            # Some builds wrap in ``res``.
            inner = item.get("res") if isinstance(item.get("res"), (list, dict)) else None
            if inner is not None:
                texts.extend(_extract_texts(inner))
                continue
        # Legacy shape: item is a list of ``[box, (text, score)]``.
        if isinstance(item, list):
            for line in item:
                try:
                    payload = line[1]
                    if isinstance(payload, (list, tuple)) and payload:
                        text = payload[0]
                    else:
                        text = payload
                    if isinstance(text, str) and text.strip():
                        texts.append(text)
                except Exception:  # noqa: BLE001
                    continue
    return texts


def _run_inference(ocr, image_path: str):
    """Call PaddleOCR, preferring the 3.x ``predict`` API."""
    predict = getattr(ocr, "predict", None)
    if callable(predict):
        return predict(image_path)
    return ocr.ocr(image_path)


async def ocr_image(image_bytes: bytes) -> str:
    ocr = get_ocr()
    if ocr is None or _mock_mode:
        raise RuntimeError("OCR_UNAVAILABLE")
    tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
    tmp.write(image_bytes)
    tmp.close()
    try:
        result = _run_inference(ocr, tmp.name)
        texts = _extract_texts(result)
        return "\n".join(texts)
    except Exception as e:  # noqa: BLE001
        logger.error(f"OCR inference error: {e}")
        raise RuntimeError(f"OCR_INFERENCE_ERROR: {e}")
    finally:
        try:
            os.unlink(tmp.name)
        except OSError:
            pass