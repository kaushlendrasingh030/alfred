import os
import io
import base64
import logging
from typing import Any, Dict, Optional, Tuple, List
from pathlib import Path

try:
    import pyautogui
except Exception:  # pragma: no cover - import may fail in headless/test envs
    pyautogui = None
try:
    from . import vision_tools
except Exception:
    import vision_tools

try:
    from . import system_tools
except Exception:
    import system_tools

WORKSPACE_ROOT = Path(os.environ.get("ALFRED_WORKSPACE", Path.cwd())).resolve()
LOGGER = logging.getLogger("alfred.tools")


def _automation_allowed() -> bool:
    """Automation (mouse/keyboard) requires explicit enablement via env var.

    Set `ALFRED_ALLOW_AUTOMATION=1` to enable pyautogui actions.
    """
    return os.environ.get("ALFRED_ALLOW_AUTOMATION") == "1"


def _ensure_pyautogui() -> None:
    if pyautogui is None:
        raise RuntimeError("pyautogui is not available in this environment")


def move_mouse(x: int, y: int, duration: float = 0.0) -> Dict[str, Any]:
    if not _automation_allowed():
        return {"error": "automation-disabled", "reason": "Set ALFRED_ALLOW_AUTOMATION=1 to enable"}
    _ensure_pyautogui()
    pyautogui.moveTo(x, y, duration=duration)
    return {"status": "moved", "x": x, "y": y, "duration": duration}


def click(x: Optional[int] = None, y: Optional[int] = None, button: str = "left") -> Dict[str, Any]:
    if not _automation_allowed():
        return {"error": "automation-disabled", "reason": "Set ALFRED_ALLOW_AUTOMATION=1 to enable"}
    _ensure_pyautogui()
    if x is not None and y is not None:
        pyautogui.click(x=x, y=y, button=button)
    else:
        pyautogui.click(button=button)
    return {"status": "clicked", "x": x, "y": y, "button": button}


def type_text(text: str, interval: float = 0.0) -> Dict[str, Any]:
    if not _automation_allowed():
        return {"error": "automation-disabled", "reason": "Set ALFRED_ALLOW_AUTOMATION=1 to enable"}
    _ensure_pyautogui()
    pyautogui.write(text, interval=interval)
    return {"status": "typed", "length": len(text)}


def screenshot(region: Optional[Tuple[int, int, int, int]] = None) -> Dict[str, Any]:
    """Capture a screenshot and return a base64-encoded PNG.

    `region` if provided should be (left, top, width, height).
    """
    _ensure_pyautogui()
    img = pyautogui.screenshot(region=tuple(region) if region else None)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    b = buf.getvalue()
    return {"image_base64": base64.b64encode(b).decode(), "size": len(b)}


def _resolve_workspace_path(path: str) -> Path:
    p = (WORKSPACE_ROOT / Path(path)).resolve()
    try:
        if not p.is_relative_to(WORKSPACE_ROOT):
            raise PermissionError("path outside workspace")
    except AttributeError:
        # Fallback for very old Python versions (not expected here)
        if str(p).startswith(str(WORKSPACE_ROOT)) is False:
            raise PermissionError("path outside workspace")
    return p


def read_file(path: str, as_base64: bool = False) -> Dict[str, Any]:
    p = _resolve_workspace_path(path)
    if not p.exists():
        return {"error": "not_found", "path": str(p)}
    data = p.read_bytes()
    if as_base64:
        return {"content_base64": base64.b64encode(data).decode(), "path": str(p)}
    try:
        text = data.decode("utf-8")
        return {"content": text, "path": str(p)}
    except Exception:
        return {"content_base64": base64.b64encode(data).decode(), "path": str(p)}


def write_file(path: str, content: str, encoding: str = "utf-8", overwrite: bool = True) -> Dict[str, Any]:
    p = _resolve_workspace_path(path)
    if p.exists() and not overwrite:
        return {"error": "exists", "path": str(p)}
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding=encoding)
    return {"status": "written", "path": str(p), "size": p.stat().st_size}


def list_files(path: str = ".") -> Dict[str, Any]:
    p = _resolve_workspace_path(path)
    if not p.exists():
        return {"error": "not_found", "path": str(p)}
    entries: List[Dict[str, Any]] = []
    for child in sorted(p.iterdir()):
        entries.append({"name": child.name, "is_dir": child.is_dir(), "size": child.stat().st_size if child.is_file() else None})
    return {"path": str(p), "entries": entries}


def update_ui_style(style: Dict[str, Any]) -> Dict[str, Any]:
    """Write a ui_style.json file the Flet UI will read to update colors/sizes.

    This operation is sensitive (affects UI) but not as critical as code-modification.
    """
    try:
        p = WORKSPACE_ROOT / "ui_style.json"
        p.write_text(json.dumps(style, ensure_ascii=False, indent=2), encoding="utf-8")
        return {"status": "written", "path": str(p)}
    except Exception as e:
        return {"error": "write-failed", "message": str(e)}


TOOL_REGISTRY = {
    "move_mouse": move_mouse,
    "click": click,
    "type_text": type_text,
    "screenshot": screenshot,
    "read_file": read_file,
    "write_file": write_file,
    "list_files": list_files,
    # vision and self-modify tools
    "get_screen_vision": vision_tools.get_screen_vision,
    "modify_alfred_code": system_tools.modify_alfred_code,
    "list_workspace_files": system_tools.list_workspace_files,
    "update_ui_style": update_ui_style,
    "apply_system_upgrade": system_tools.apply_system_upgrade,
}

# Lightweight tool schema metadata for model-side function calling.
# Each schema includes a short description and a JSON-schema-like `parameters` description
# so the model can construct valid arguments. This is used by `assistant.py` when
# asking the model to call local tools.
TOOL_SCHEMAS = {
    "move_mouse": {
        "description": "Move the mouse cursor to (x,y) with optional duration seconds.",
        "sensitive": True,
        "parameters": {"type": "object", "properties": {"x": {"type": "integer"}, "y": {"type": "integer"}, "duration": {"type": "number"}}, "required": ["x","y"]},
    },
    "click": {
        "description": "Click at coordinates (x,y) or current position if omitted.",
        "sensitive": True,
        "parameters": {"type": "object", "properties": {"x": {"type": "integer"}, "y": {"type": "integer"}, "button": {"type": "string"}}, "required": []},
    },
    "type_text": {
        "description": "Type the given text into the active window.",
        "sensitive": True,
        "parameters": {"type": "object", "properties": {"text": {"type": "string"}, "interval": {"type": "number"}}, "required": ["text"]},
    },
    "screenshot": {
        "description": "Capture a screenshot and return it base64-encoded. Optionally provide region [left,top,width,height].",
        "parameters": {"type": "object", "properties": {"region": {"type": "array", "items": {"type": "integer"}}}, "required": []},
    },
    "get_screen_vision": {
        "description": "Capture the full screen or region and return base64 PNG for Vision analysis.",
        "parameters": {"type": "object", "properties": {"region": {"type": "array", "items": {"type": "integer"}}}, "required": []},
    },
    "read_file": {
        "description": "Read a file under the workspace and return its contents (text or base64).",
        "parameters": {"type": "object", "properties": {"path": {"type": "string"}, "as_base64": {"type": "boolean"}}, "required": ["path"]},
    },
    "write_file": {
        "description": "Write text content to a file under the workspace. Overwrites by default.",
        "sensitive": True,
        "parameters": {"type": "object", "properties": {"path": {"type": "string"}, "content": {"type": "string"}, "overwrite": {"type": "boolean"}}, "required": ["path","content"]},
    },
    "list_files": {
        "description": "List files and directories under a workspace path.",
        "parameters": {"type": "object", "properties": {"path": {"type": "string"}}, "required": []},
    },
    "list_workspace_files": {
        "description": "List all files in the configured workspace (recursive).",
        "parameters": {"type": "object", "properties": {} , "required": []},
    },
    "modify_alfred_code": {
        "description": "Overwrite a Python file in the workspace to modify Alfred's code. Requires ALFRED_ALLOW_SELF_MODIFY=1",
        "sensitive": True,
        "parameters": {"type": "object", "properties": {"filename": {"type": "string"}, "new_content": {"type": "string"}}, "required": ["filename","new_content"]},
    },
    "apply_system_upgrade": {
        "description": "Apply a code upgrade by overwriting an allowed system file. Requires ALFRED_ALLOW_SELF_MODIFY=1",
        "sensitive": True,
        "parameters": {"type": "object", "properties": {"target_file": {"type": "string"}, "code_snippet": {"type": "string"}}, "required": ["target_file","code_snippet"]},
    },
    "update_ui_style": {
        "description": "Update the Flet UI style by writing ui_style.json in the workspace.",
        "parameters": {"type": "object", "properties": {"bar_color": {"type": "string"}, "accent": {"type": "string"}}, "required": []},
    },
}


def execute_tool(name: str, args: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    args = args or {}
    fn = TOOL_REGISTRY.get(name)
    if not fn:
        return {"error": "unknown_tool", "tool": name}
    try:
        return fn(**args)
    except TypeError as e:
        return {"error": "bad_arguments", "message": str(e)}
    except Exception as e:
        LOGGER.exception("tool failed")
        return {"error": "exception", "message": str(e)}
