from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import os
from typing import Dict, Any

from assistant import GeminiAssistant
import tools

app = FastAPI(title="Alfred — Web UI")

templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

# single assistant instance
assistant = GeminiAssistant()


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/api/message")
async def post_message(payload: Dict[str, Any]):
    msg = payload.get("message")
    if not msg:
        raise HTTPException(status_code=400, detail="message required")
    try:
        out = assistant.process_text(msg)
        # generator check
        if hasattr(out, "__iter__") and not isinstance(out, str):
            text = "".join(list(out))
        else:
            text = out
        return JSONResponse({"reply": text})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/confirm")
async def api_confirm():
    try:
        out = assistant.process_text("/confirm")
        return JSONResponse({"reply": out})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/cancel")
async def api_cancel():
    try:
        out = assistant.process_text("/cancel")
        return JSONResponse({"reply": out})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/list_files")
async def api_list_files():
    res = tools.execute_tool("list_workspace_files", {})
    return JSONResponse(res)


@app.post("/api/screenshot")
async def api_screenshot():
    res = tools.execute_tool("get_screen_vision", {})
    return JSONResponse(res)


@app.post("/api/vision_analyze")
async def api_vision_analyze(payload: Dict[str, Any]):
    image_b64 = payload.get("image_base64")
    instruction = payload.get("instruction", "Describe the image.")
    if not image_b64:
        raise HTTPException(status_code=400, detail="image_base64 required")
    out = assistant.call_gemini_vision(image_b64, instruction)
    return JSONResponse(out)


@app.post("/api/modify_code")
async def api_modify_code(payload: Dict[str, Any]):
    filename = payload.get("filename")
    new_content = payload.get("new_content")
    if not filename or new_content is None:
        raise HTTPException(status_code=400, detail="filename and new_content required")
    # rely on system_tools gating (ALFRED_ALLOW_SELF_MODIFY)
    res = tools.execute_tool("modify_alfred_code", {"filename": filename, "new_content": new_content})
    return JSONResponse(res)
