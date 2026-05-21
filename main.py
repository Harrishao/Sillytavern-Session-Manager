"""
SillyTavern Session Manager
基于 FastAPI 的 Web 服务，提供通用消息输入接口和 Web 调试面板
"""
import os
import sys
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
import uvicorn

import core

# ---------- FastAPI 应用 ----------

app = FastAPI(title="ST Session Manager", version="0.1.0")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")

HTML_PATH = os.path.join(STATIC_DIR, "index.html")
with open(HTML_PATH, "r", encoding="utf-8") as f:
    INDEX_HTML = f.read()


# ---------- 生命周期 ----------

@app.on_event("startup")
async def on_startup():
    """服务启动时初始化浏览器"""
    print("[server] 正在启动浏览器...")
    await core.init_browser()
    print("[server] 服务已就绪")


@app.on_event("shutdown")
async def on_shutdown():
    """服务关闭时清理浏览器"""
    await core.close_browser()


# ---------- 页面 ----------

@app.get("/", response_class=HTMLResponse)
async def index():
    """Web 调试面板"""
    return INDEX_HTML


# ---------- 消息 API ----------

@app.post("/api/send")
async def api_send(request: Request):
    """
    通用消息输入接口
    POST JSON: {"text": "你好"} → 注入消息 → 等待回复 → 截图
    返回: {"content": "...", "reasoning": "...", "screenshot_path": "..."}
    """
    data = await request.json()
    text = (data.get("text", "") or "").strip()
    if not text:
        return JSONResponse({"error": "empty message"}, status_code=400)

    result = await core.send_message(text)
    if result is None:
        return JSONResponse({"error": "send failed or timeout"}, status_code=500)

    return JSONResponse(result)


# ---------- 截图 API ----------

@app.get("/api/screenshots")
async def api_list_screenshots():
    """列出 screenshot 目录下所有截图文件"""
    files = []
    screenshot_dir = core.SCREENSHOT_DIR
    if os.path.isdir(screenshot_dir):
        for f in sorted(os.listdir(screenshot_dir), reverse=True):
            if f.endswith(".png"):
                p = os.path.join(screenshot_dir, f)
                files.append({
                    "filename": f,
                    "size": os.path.getsize(p),
                    "url": f"/api/screenshot/{f}",
                })
    return JSONResponse(files)


@app.get("/api/screenshot/{filename}")
async def api_get_screenshot(filename: str):
    """获取指定截图文件"""
    path = os.path.join(core.SCREENSHOT_DIR, filename)
    if not os.path.isfile(path):
        return JSONResponse({"error": "not found"}, status_code=404)
    return FileResponse(path)


# ---------- 交互 API ----------

@app.post("/api/inject")
async def api_inject(request: Request):
    """仅注入消息，不等待回复"""
    data = await request.json()
    text = (data.get("text", "") or "").strip()
    if not text:
        return JSONResponse({"error": "empty message"}, status_code=400)
    ok = await core.inject_message(text)
    return JSONResponse({"ok": ok})


@app.post("/api/stop")
async def api_stop():
    """停止当前生成"""
    ok = await core.cancel_processing()
    return JSONResponse({"ok": ok})


@app.post("/api/swipe-left")
async def api_swipe_left():
    """左翻页（上一个备选回复）"""
    ok = await core.swipe_left()
    return JSONResponse({"ok": ok})


@app.post("/api/swipe-right")
async def api_swipe_right():
    """右翻页（下一个备选回复）"""
    result = await core.swipe_right()
    return JSONResponse({"ok": result is not None, "status": result})


@app.post("/api/regenerate")
async def api_regenerate():
    """重新生成回复"""
    ok = await core.regenerate()
    return JSONResponse({"ok": ok})


@app.get("/api/wait")
async def api_wait(timeout: float = 120.0):
    """等待当前生成完成并截图"""
    result = await core.wait_for_response(timeout=timeout)
    if result is None:
        return JSONResponse({"error": "timeout"}, status_code=500)
    screenshot_path = await core.capture_screenshot()
    result["screenshot_path"] = screenshot_path
    return JSONResponse(result)


@app.post("/api/refresh")
async def api_refresh():
    """刷新 ST 页面"""
    ok = await core.refresh_page()
    return JSONResponse({"ok": ok})


@app.get("/api/screenshot-now")
async def api_screenshot_now():
    """立即截图（不等待生成）"""
    path = await core.capture_screenshot()
    return JSONResponse({"path": path})


@app.get("/api/full-screenshot")
async def api_full_screenshot():
    """全页截图"""
    path = await core.capture_full_screenshot()
    return JSONResponse({"path": path})


# ---------- 角色卡 & 聊天管理 API ----------

@app.get("/api/characters")
async def api_characters():
    """获取角色卡列表"""
    chars = await core.fetch_characters()
    return JSONResponse(chars)


@app.get("/api/chats")
async def api_chats():
    """获取最近聊天列表"""
    chats = await core.fetch_recent_chats()
    return JSONResponse(chats)


@app.get("/api/character-chats")
async def api_character_chats(avatar_url: str):
    """获取指定角色的聊天记录"""
    chats = await core.fetch_character_chats(avatar_url)
    return JSONResponse(chats)


@app.post("/api/open-chat")
async def api_open_chat(request: Request):
    """打开指定聊天"""
    data = await request.json()
    file_name = data.get("file_name", "")
    if not file_name:
        return JSONResponse({"error": "file_name required"}, status_code=400)
    ok = await core.open_chat(file_name)
    return JSONResponse({"ok": ok})


@app.post("/api/delete-messages")
async def api_delete_messages(request: Request):
    """删除最后N条消息"""
    data = await request.json()
    n = data.get("n", 1)
    ok = await core.delete_messages(n)
    return JSONResponse({"ok": ok})


@app.post("/api/delete-chat")
async def api_delete_chat(request: Request):
    """删除指定聊天"""
    data = await request.json()
    file_name = data.get("file_name", "")
    if not file_name:
        return JSONResponse({"error": "file_name required"}, status_code=400)
    ok = await core.delete_chat(file_name)
    return JSONResponse({"ok": ok})


# ---------- 用户设定 API ----------

@app.get("/api/personas")
async def api_personas():
    """获取用户设定列表"""
    personas = await core.fetch_personas()
    return JSONResponse(personas)


@app.post("/api/select-persona")
async def api_select_persona(request: Request):
    """选择用户设定"""
    data = await request.json()
    avatar_id = data.get("avatar_id", "")
    if not avatar_id:
        return JSONResponse({"error": "avatar_id required"}, status_code=400)
    ok = await core.select_persona(avatar_id)
    return JSONResponse({"ok": ok, "current": await core.get_current_persona()})


@app.get("/api/current-persona")
async def api_current_persona():
    """获取当前激活的用户设定"""
    name = await core.get_current_persona()
    return JSONResponse({"name": name})


# ---------- 入口 ----------

def main():
    port = int(os.environ.get("PORT", 8080))
    host = os.environ.get("HOST", "127.0.0.1")
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()
