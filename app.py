# -*- coding: utf-8 -*-
"""
Daily Business Information Assistant - FastAPI Web Server
行业销售动态与商机挖掘助手 - 可视化工作台后端服务
"""

import asyncio
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
from fastapi import FastAPI, BackgroundTasks
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from config.settings import settings
from core.engine import BusinessBriefingEngine
from core.scheduler import DailyScheduler

BASE_DIR = Path(__file__).resolve().parent

app = FastAPI(
    title="Daily Business Information Assistant",
    description="每日行业商业与销售情报助手 Web 工作台",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

static_dir = BASE_DIR / "web" / "static"
static_dir.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

output_dir = settings.get_output_dir()
app.mount("/output", StaticFiles(directory=str(output_dir)), name="output")

engine = BusinessBriefingEngine(settings)
scheduler = None


def get_or_create_scheduler():
    global scheduler
    if scheduler is None:
        async def scheduled_run():
            await engine.run()
        daily_time = settings.scheduler.get("daily_time", "08:30")
        scheduler = DailyScheduler(daily_time, scheduled_run)
        if settings.scheduler.get("enabled", False):
            scheduler.start()
    return scheduler


@app.on_event("startup")
async def startup_event():
    get_or_create_scheduler()


@app.get("/", response_class=HTMLResponse)
async def index():
    html_file = BASE_DIR / "web" / "index.html"
    if html_file.exists():
        with open(html_file, "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>Web 工作台界面文件未找到</h1>"


@app.get("/api/config")
async def get_config():
    cfg = settings.config.copy()
    ai_cfg = cfg.get("ai", {}).copy()
    raw_key = settings.get_api_key()
    if raw_key:
        ai_cfg["api_key_masked"] = raw_key[:4] + "********" + raw_key[-4:] if len(raw_key) > 8 else "********"
        ai_cfg["has_key"] = True
    else:
        ai_cfg["api_key_masked"] = ""
        ai_cfg["has_key"] = False
    ai_cfg.pop("api_key", None)
    cfg["ai"] = ai_cfg
    return cfg


class ConfigUpdateRequest(BaseModel):
    industries: Optional[Dict[str, Any]] = None
    business_domains: Optional[Dict[str, Any]] = None
    bidding_keywords: Optional[list] = None
    sources: Optional[Dict[str, Any]] = None
    ai: Optional[Dict[str, Any]] = None
    scheduler: Optional[Dict[str, Any]] = None
    app: Optional[Dict[str, Any]] = None


@app.post("/api/config")
async def update_config(req: ConfigUpdateRequest):
    cfg = settings.config
    if req.industries is not None:
        cfg["industries"] = req.industries
    if req.business_domains is not None:
        cfg["business_domains"] = req.business_domains
    if req.bidding_keywords is not None:
        cfg["bidding_keywords"] = req.bidding_keywords
    if req.sources is not None:
        cfg["sources"] = req.sources
    if req.ai is not None:
        new_key = req.ai.get("api_key")
        if new_key and not new_key.startswith("****"):
            cfg.setdefault("ai", {})["api_key"] = new_key
        for k in ["provider", "model", "base_url", "temperature", "prompt", "enabled"]:
            if k in req.ai:
                cfg.setdefault("ai", {})[k] = req.ai[k]
    if req.scheduler is not None:
        cfg["scheduler"] = req.scheduler
        sched = get_or_create_scheduler()
        sched.update_time(req.scheduler.get("daily_time", "08:30"))
        if req.scheduler.get("enabled", False):
            sched.start()
        else:
            sched.stop()
    if req.app is not None:
        cfg["app"] = req.app

    success = settings.save(cfg)
    return {"success": success, "message": "销售情报配置更新成功" if success else "保存失败"}


@app.get("/api/status")
async def get_status():
    status_data = engine.status.to_dict()
    sched = get_or_create_scheduler()
    status_data["scheduler_enabled"] = sched.is_running
    status_data["scheduler_time"] = sched.target_time_str
    status_data["next_run_seconds"] = int(sched.get_seconds_until_next_run()) if sched.is_running else 0
    return status_data


@app.post("/api/task/start")
async def start_task(background_tasks: BackgroundTasks):
    if engine.status.is_running:
        return JSONResponse(status_code=400, content={"error": "已有商机采集任务正在执行中"})
    background_tasks.add_task(engine.run)
    return {"success": True, "message": "行业销售动态采集任务已启动"}


@app.get("/api/task/logs/stream")
async def stream_logs():
    async def event_generator():
        q = asyncio.Queue()
        def listener(msg):
            q.put_nowait(msg)
        engine.add_log_listener(listener)
        for log in engine.status.logs[-20:]:
            yield f"data: {log}\n\n"
        try:
            while True:
                msg = await q.get()
                yield f"data: {msg}\n\n"
        except asyncio.CancelledError:
            if listener in engine._log_listeners:
                engine._log_listeners.remove(listener)
    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.post("/api/test/ai")
async def test_ai_connection(payload: Dict[str, Any]):
    provider = payload.get("provider", "gemini").lower()
    api_key = payload.get("api_key") or settings.get_api_key()
    model = payload.get("model", "gemini-2.5-flash-lite")
    base_url = payload.get("base_url")

    if not api_key:
        return {"success": False, "error": "未提供 API Key"}

    try:
        if provider == "gemini":
            from google import genai
            from google.genai import types
            client = genai.Client(api_key=api_key)
            resp = client.models.generate_content(
                model=model,
                contents="请回复商机评估服务正常六个字。",
                config=types.GenerateContentConfig(max_output_tokens=20)
            )
            return {"success": True, "reply": resp.text.strip()}
        else:
            from openai import OpenAI
            provider_urls = {
                "deepseek": "https://api.deepseek.com/v1",
                "openai": "https://api.openai.com/v1",
                "qwen": "https://dashscope.aliyuncs.com/compatible-mode/v1",
                "kimi": "https://api.moonshot.cn/v1",
                "ollama": "http://localhost:11434/v1"
            }
            resolved_base_url = base_url or provider_urls.get(provider)
            client = OpenAI(api_key=api_key, base_url=resolved_base_url)
            resp = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": "请回复商机评估服务正常六个字。"}],
                max_tokens=20
            )
            return {"success": True, "reply": resp.choices[0].message.content.strip()}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.get("/api/reports")
async def list_reports():
    out_dir = settings.get_output_dir()
    files = []
    for p in sorted(out_dir.glob("*.*"), key=os.path.getmtime, reverse=True):
        if p.suffix.lower() in [".png", ".json", ".md"]:
            files.append({
                "filename": p.name,
                "type": p.suffix.lower().replace(".", ""),
                "size": p.stat().st_size,
                "time": datetime.fromtimestamp(p.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
                "url": f"/output/{p.name}"
            })
    return files


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8001))
    print(f"💼 启动 Daily Business Information Assistant: http://localhost:{port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
