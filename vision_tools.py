import os
import io
import base64
from pathlib import Path
from typing import Dict, Any

try:
    import pyautogui
except Exception:  # pragma: no cover
    pyautogui = None

try:
    from PIL import Image
except Exception:
    Image = None

WORKSPACE_ROOT = Path(os.environ.get("ALFRED_WORKSPACE", Path.cwd())).resolve()


def get_screen_vision(region: tuple = None) -> Dict[str, Any]:
    """Take a screenshot and return base64-encoded PNG string and metadata.

    `region` is optionally (left, top, width, height).
    """
    if pyautogui is None:
        return {"error": "pyautogui-unavailable"}

    try:
        img = pyautogui.screenshot(region=tuple(region) if region else None)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        b = buf.getvalue()
        return {"image_base64": base64.b64encode(b).decode("utf-8"), "size": len(b)}
    except Exception as e:
        return {"error": "screenshot-failed", "message": str(e)}
