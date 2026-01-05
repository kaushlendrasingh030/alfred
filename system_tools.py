import os
from pathlib import Path
from typing import Dict, Any, List

WORKSPACE_ROOT = Path(os.environ.get("ALFRED_WORKSPACE", Path.cwd())).resolve()


def _resolve_workspace_path(filename: str) -> Path:
    p = (WORKSPACE_ROOT / Path(filename)).resolve()
    try:
        if not p.is_relative_to(WORKSPACE_ROOT):
            raise PermissionError("path outside workspace")
    except AttributeError:
        if str(p).startswith(str(WORKSPACE_ROOT)) is False:
            raise PermissionError("path outside workspace")
    return p


def modify_alfred_code(filename: str, new_content: str) -> Dict[str, Any]:
    """Overwrite a Python file in the workspace to allow Alfred to self-modify.

    This operation is sensitive and requires ALFRED_ALLOW_SELF_MODIFY=1 in the environment.
    """
    import os

    if os.environ.get("ALFRED_ALLOW_SELF_MODIFY") != "1":
        return {"error": "self-modify-disabled", "reason": "Set ALFRED_ALLOW_SELF_MODIFY=1 to enable"}

    if not filename.endswith(".py"):
        return {"error": "invalid-filename", "message": "Only .py files can be modified"}

    try:
        p = _resolve_workspace_path(filename)
    except Exception as e:
        return {"error": "path-error", "message": str(e)}

    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(new_content, encoding="utf-8")
        return {"status": "written", "path": str(p)}
    except Exception as e:
        return {"error": "write-failed", "message": str(e)}


def list_workspace_files() -> Dict[str, Any]:
    files = []
    for p in sorted(WORKSPACE_ROOT.rglob("*")):
        files.append({"path": str(p.relative_to(WORKSPACE_ROOT)), "is_dir": p.is_dir()})
    return {"files": files}


def apply_system_upgrade(code_snippet: str, target_file: str) -> Dict[str, Any]:
    """Apply a system upgrade by overwriting allowed target files with the provided code snippet.

    This is gated by ALFRED_ALLOW_SELF_MODIFY and restricted to a safe allowlist.
    """
    import os

    if os.environ.get("ALFRED_ALLOW_SELF_MODIFY") != "1":
        return {"error": "self-modify-disabled", "reason": "Set ALFRED_ALLOW_SELF_MODIFY=1 to enable"}

    allowlist = {"limbs.py", "main_app.py", "interface.py", "app.py"}
    if target_file not in allowlist:
        return {"error": "target-not-allowed", "allowed": list(allowlist)}

    try:
        p = _resolve_workspace_path(target_file)
    except Exception as e:
        return {"error": "path-error", "message": str(e)}

    try:
        p.write_text(code_snippet, encoding="utf-8")
        return {"status": "applied", "path": str(p)}
    except Exception as e:
        return {"error": "write-failed", "message": str(e)}
