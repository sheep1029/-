"""
InnoCore API 主应用
"""

from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse
from contextlib import asynccontextmanager
import logging
import uvicorn
from datetime import datetime, timezone

from core.config import get_config
from core.database import db_manager
from core.vector_store import vector_store_manager
from agents.controller import agent_controller
from .routes import papers, users, tasks, analysis, writing, citations, workflow

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时初始化
    logger.info("正在启动InnoCore AI...")
    
    # 初始化数据库（可选）
    try:
        await db_manager.initialize()
        logger.info("数据库初始化完成")
    except Exception as e:
        logger.warning(f"数据库初始化失败（将以无数据库模式运行）: {str(e)}")
    
    # 初始化向量存储（可选）
    try:
        await vector_store_manager.initialize()
        logger.info("向量存储初始化完成")
    except Exception as e:
        logger.warning(f"向量存储初始化失败（将以无向量存储模式运行）: {str(e)}")
    
    # 初始化智能体控制器（可选）
    try:
        await agent_controller.initialize()
        logger.info("智能体控制器初始化完成")
        
        # 启动任务处理器
        import asyncio
        asyncio.create_task(agent_controller.start_task_processor())
        logger.info("任务处理器已启动")
    except Exception as e:
        logger.warning(f"智能体控制器初始化失败: {str(e)}")
    
    logger.info("InnoCore AI 启动完成")
    
    yield
    
    # 关闭时清理
    logger.info("正在关闭InnoCore AI...")
    await agent_controller.shutdown()
    await db_manager.close()
    await vector_store_manager.close()
    logger.info("InnoCore AI已关闭")

# 创建FastAPI应用
app = FastAPI(
    title="InnoCore Research API",
    description="智能科研创新助手API",
    version="0.1.0",
    lifespan=lifespan
)

# 配置CORS
config = get_config()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应该限制具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(papers.router, prefix="/api/v1/papers", tags=["papers"])
app.include_router(users.router, prefix="/api/v1/users", tags=["users"])
app.include_router(tasks.router, prefix="/api/v1/tasks", tags=["tasks"])
app.include_router(analysis.router, prefix="/api/v1/analysis", tags=["analysis"])
app.include_router(writing.router, prefix="/api/v1/writing", tags=["writing"])
app.include_router(citations.router, prefix="/api/v1/citations", tags=["citations"])
app.include_router(workflow.router, prefix="/api/v1/workflow", tags=["workflow"])

# 挂载静态文件
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

# 获取项目根目录
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")

# 挂载静态资源
if os.path.exists(os.path.join(FRONTEND_DIR, "static")):
    app.mount("/static", StaticFiles(directory=os.path.join(FRONTEND_DIR, "static")), name="static")

# 根路径 - 返回前端页面
@app.get("/")
async def root():
    """根路径 - 返回前端首页"""
    index_path = os.path.join(FRONTEND_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {
        "message": "Welcome to InnoCore Research API",
        "version": "0.1.0",
        "status": "running"
    }

# 健康检查
@app.get("/health")
async def health_check():
    """健康检查"""
    try:
        agent_status = await agent_controller.get_agent_status()

        return {
            "status": "healthy",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "agents": agent_status.get("agents", {}),
            "stats": {
                "active_tasks": agent_status.get("active_tasks", 0),
                "queued_tasks": agent_status.get("queued_tasks", 0),
                "completed_tasks": agent_status.get("completed_tasks", 0),
                "max_concurrent": agent_status.get("max_concurrent", 0)
            }
        }
    except Exception as e:
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "error": str(e)
            }
        )


@app.get("/health/ui", response_class=HTMLResponse)
async def health_ui():
    html = """<!doctype html>
<html lang=\"zh-CN\">
  <head>
    <meta charset=\"utf-8\" />
    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
    <title>Health Status · InnoCore Research</title>
    <style>
      :root {
        --bg0: #070a17;
        --bg1: #0b1028;
        --surface: rgba(255, 255, 255, 0.86);
        --border: rgba(255, 255, 255, 0.55);
        --text: #0f172a;
        --muted: #475569;
        --primary: #4f46e5;
        --success: #16a34a;
        --danger: #dc2626;
        --warning: #f59e0b;
        --shadow: 0 18px 55px rgba(2, 6, 23, 0.28);
        --ring: 0 0 0 4px rgba(79, 70, 229, 0.16);
        --radius: 18px;
      }
      * { box-sizing: border-box; margin: 0; padding: 0; }
      body {
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, 'Noto Sans', sans-serif;
        min-height: 100vh;
        color: var(--text);
        background:
          radial-gradient(900px 520px at 12% 18%, rgba(79, 70, 229, 0.55), transparent 60%),
          radial-gradient(820px 520px at 86% 18%, rgba(124, 58, 237, 0.45), transparent 55%),
          radial-gradient(980px 620px at 50% 92%, rgba(56, 189, 248, 0.14), transparent 65%),
          linear-gradient(180deg, var(--bg0), var(--bg1));
      }
      .container { max-width: 980px; margin: 0 auto; padding: 28px 18px 44px; }
      header { text-align: center; padding: 42px 0 18px; color: rgba(255,255,255,0.92); }
      header h1 { font-size: clamp(1.9rem, 3.4vw, 2.6rem); letter-spacing: -0.02em; text-shadow: 0 18px 38px rgba(0,0,0,0.35); }
      header p { margin-top: 10px; color: rgba(255,255,255,0.78); line-height: 1.6; }
      .card {
        background: var(--surface);
        border: 1px solid var(--border);
        border-radius: var(--radius);
        box-shadow: var(--shadow);
        backdrop-filter: blur(14px);
        -webkit-backdrop-filter: blur(14px);
        padding: 18px;
      }
      .topbar { display: flex; justify-content: space-between; align-items: center; gap: 12px; flex-wrap: wrap; }
      .badge {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        padding: 8px 12px;
        border-radius: 999px;
        font-weight: 800;
        letter-spacing: -0.01em;
        border: 1px solid rgba(2, 6, 23, 0.10);
        background: rgba(255,255,255,0.70);
      }
      .badge[data-level=\"ok\"] { color: #065f46; border-color: rgba(22, 163, 74, 0.22); background: rgba(22, 163, 74, 0.10); }
      .badge[data-level=\"warn\"] { color: #92400e; border-color: rgba(245, 158, 11, 0.25); background: rgba(245, 158, 11, 0.12); }
      .badge[data-level=\"bad\"] { color: #7f1d1d; border-color: rgba(220, 38, 38, 0.20); background: rgba(220, 38, 38, 0.10); }
      .btn {
        appearance: none;
        border: 1px solid rgba(2, 6, 23, 0.12);
        background: linear-gradient(135deg, var(--primary) 0%, #7c3aed 100%);
        color: rgba(255,255,255,0.98);
        padding: 10px 14px;
        border-radius: 12px;
        cursor: pointer;
        font-weight: 700;
        transition: box-shadow 0.16s ease, transform 0.16s ease;
        box-shadow: 0 10px 22px rgba(79, 70, 229, 0.22);
      }
      .btn:hover { transform: translateY(-1px); box-shadow: 0 14px 28px rgba(79, 70, 229, 0.26); }
      .btn:focus-visible { outline: none; box-shadow: var(--ring), 0 14px 28px rgba(79, 70, 229, 0.26); }
      .muted { color: var(--muted); }
      .grid { display: grid; grid-template-columns: repeat(12, 1fr); gap: 12px; margin-top: 14px; }
      .tile {
        grid-column: span 6;
        background: rgba(255,255,255,0.70);
        border: 1px solid rgba(2, 6, 23, 0.10);
        border-radius: 14px;
        padding: 14px;
      }
      .tile h2 { font-size: 1.0rem; letter-spacing: -0.01em; margin-bottom: 8px; }
      .row { display: flex; align-items: center; justify-content: space-between; gap: 12px; }
      .kpis { display: flex; flex-wrap: wrap; gap: 10px; margin-top: 12px; }
      .kpi { display: inline-flex; align-items: baseline; gap: 8px; padding: 10px 12px; border-radius: 14px; border: 1px solid rgba(2, 6, 23, 0.10); background: rgba(255,255,255,0.78); }
      .kpi .label { color: var(--muted); font-weight: 700; }
      .kpi .value { font-weight: 900; letter-spacing: -0.02em; }
      .pill {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 6px 10px;
        border-radius: 999px;
        font-weight: 800;
        font-size: 0.9rem;
        border: 1px solid rgba(2, 6, 23, 0.10);
        background: rgba(255,255,255,0.82);
      }
      .pill[data-state=\"connected\"] { color: #065f46; border-color: rgba(22, 163, 74, 0.20); background: rgba(22, 163, 74, 0.10); }
      .pill[data-state=\"unavailable\"] { color: #7f1d1d; border-color: rgba(220, 38, 38, 0.20); background: rgba(220, 38, 38, 0.10); }
      .pill[data-state=\"unknown\"] { color: #0f172a; border-color: rgba(2, 6, 23, 0.12); background: rgba(2, 6, 23, 0.06); }
      .agent-grid { display: grid; grid-template-columns: repeat(12, 1fr); gap: 12px; margin-top: 14px; }
      .agent-card {
        grid-column: span 6;
        background: rgba(255,255,255,0.72);
        border: 1px solid rgba(2, 6, 23, 0.10);
        border-radius: 16px;
        padding: 14px;
        box-shadow: 0 10px 22px rgba(2, 6, 23, 0.08);
      }
      .agent-title { display: flex; align-items: center; justify-content: space-between; gap: 12px; }
      .agent-name { font-weight: 900; letter-spacing: -0.02em; }
      .agent-meta { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 10px; margin-top: 10px; }
      .agent-meta .item { padding: 10px 12px; border-radius: 14px; border: 1px solid rgba(2, 6, 23, 0.10); background: rgba(255,255,255,0.86); }
      .agent-meta .item .k { color: var(--muted); font-weight: 700; font-size: 0.86rem; }
      .agent-meta .item .v { margin-top: 4px; font-weight: 900; }
      pre {
        margin-top: 12px;
        padding: 14px;
        border-radius: 14px;
        border: 1px solid rgba(2, 6, 23, 0.10);
        background: rgba(255,255,255,0.78);
        overflow-x: auto;
        font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', monospace;
        font-size: 0.92rem;
        line-height: 1.65;
      }
      @media (max-width: 820px) {
        .tile { grid-column: span 12; }
        .agent-card { grid-column: span 12; }
      }
    </style>
  </head>
  <body>
    <div class=\"container\">
      <header>
        <h1>🩺 Health Status</h1>
        <p>更友好的健康检查页面（原始 JSON 仍可访问：<span class=\"muted\">/health</span>）</p>
      </header>
      <main class=\"card\">
        <div class=\"topbar\">
          <div>
            <div id=\"overall\" class=\"badge\" data-level=\"unknown\">Loading…</div>
            <div class=\"muted\" style=\"margin-top: 8px\">更新时间：<span id=\"ts\">—</span></div>
          </div>
          <div class=\"row\">
            <button class=\"btn\" id=\"refresh\" type=\"button\">刷新</button>
            <a class=\"btn\" href=\"/docs\" style=\"text-decoration:none\">API 文档</a>
          </div>
        </div>

        <div class=\"kpis\">
          <div class=\"kpi\"><span class=\"label\">Active Tasks</span><span class=\"value\" id=\"kpi-active\">—</span></div>
          <div class=\"kpi\"><span class=\"label\">Queued</span><span class=\"value\" id=\"kpi-queued\">—</span></div>
          <div class=\"kpi\"><span class=\"label\">Completed</span><span class=\"value\" id=\"kpi-completed\">—</span></div>
          <div class=\"kpi\"><span class=\"label\">Max Concurrent</span><span class=\"value\" id=\"kpi-max\">—</span></div>
        </div>

        <div class=\"row\" style=\"margin-top: 16px\">
          <h2 style=\"font-size: 1.05rem; letter-spacing: -0.01em\">Agents</h2>
          <div id=\"agents\" class=\"pill\" data-state=\"unknown\">Unknown</div>
        </div>
        <div class=\"muted\" style=\"margin-top: 6px\">仅展示 Agents 探查结果；原始数据见下方</div>

        <div class=\"agent-grid\" id=\"agent-grid\"></div>

        <pre id=\"raw\">Loading…</pre>
      </main>
    </div>

    <script>
      const $ = (id) => document.getElementById(id)

      function setPill(el, state, label) {
        el.dataset.state = state
        el.textContent = label
      }

      function setOverall(level, label) {
        const el = $('overall')
        el.dataset.level = level
        el.textContent = label
      }

      function escapeHtml(str) {
        return String(str)
          .replaceAll('&', '&amp;')
          .replaceAll('<', '&lt;')
          .replaceAll('>', '&gt;')
          .replaceAll('"', '&quot;')
          .replaceAll("'", '&#39;')
      }

      function agentLabel(key) {
        const map = {
          hunter: 'Hunter',
          miner: 'Miner',
          coach: 'Coach',
          validator: 'Validator',
          workflow: 'Workflow'
        }
        return map[key] || key
      }

      function agentStatePill(state) {
        const normalized = (state || '').toLowerCase()
        const okStates = new Set(['idle', 'ready', 'running'])
        const level = okStates.has(normalized) ? 'connected' : (normalized ? 'unavailable' : 'unknown')
        const label = state || 'unknown'
        return { level, label }
      }

      async function load() {
        $('refresh').disabled = true
        try {
          const res = await fetch('/health', { cache: 'no-store' })
          const data = await res.json()

          $('raw').textContent = JSON.stringify(data, null, 2)
          $('ts').textContent = data.timestamp || '—'

          const agents = data?.agents && typeof data.agents === 'object' ? data.agents : {}
          const stats = data?.stats && typeof data.stats === 'object' ? data.stats : {}

          $('kpi-active').textContent = stats.active_tasks ?? '—'
          $('kpi-queued').textContent = stats.queued_tasks ?? '—'
          $('kpi-completed').textContent = stats.completed_tasks ?? '—'
          $('kpi-max').textContent = stats.max_concurrent ?? '—'

          const agentKeys = Object.keys(agents)
          const agentsOk = agentKeys.length > 0
          setPill($('agents'), agentsOk ? 'connected' : 'unavailable', agentsOk ? `${agentKeys.length} Agents` : 'Unavailable')

          const grid = $('agent-grid')
          grid.innerHTML = ''
          agentKeys.sort().forEach((key) => {
            const a = agents[key] || {}
            const { level, label } = agentStatePill(a.state)
            const createdAt = a.created_at ? new Date(a.created_at).toLocaleString() : '—'
            const card = document.createElement('section')
            card.className = 'agent-card'
            card.innerHTML = `
              <div class="agent-title">
                <div class="agent-name">${escapeHtml(agentLabel(key))}</div>
                <div class="pill" data-state="${level}">${escapeHtml(label)}</div>
              </div>
              <div class="agent-meta">
                <div class="item"><div class="k">Tools</div><div class="v">${escapeHtml(a.tools_count ?? '—')}</div></div>
                <div class="item"><div class="k">History</div><div class="v">${escapeHtml(a.history_count ?? '—')}</div></div>
                <div class="item" style="grid-column: span 2"><div class="k">Created</div><div class="v">${escapeHtml(createdAt)}</div></div>
              </div>
            `
            grid.appendChild(card)
          })

          if (res.ok && data.status === 'healthy') {
            setOverall('ok', 'Healthy')
          } else {
            setOverall('bad', 'Unhealthy')
          }
        } catch (e) {
          $('raw').textContent = String(e)
          $('ts').textContent = '—'
          $('kpi-active').textContent = '—'
          $('kpi-queued').textContent = '—'
          $('kpi-completed').textContent = '—'
          $('kpi-max').textContent = '—'
          setPill($('agents'), 'unknown', 'Unknown')
          $('agent-grid').innerHTML = ''
          setOverall('bad', 'Unhealthy')
        } finally {
          $('refresh').disabled = false
        }
      }

      $('refresh').addEventListener('click', load)
      load()
    </script>
  </body>
</html>"""

    return HTMLResponse(content=html)

# 全局异常处理
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """全局异常处理器"""
    logger.error(f"全局异常: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": str(exc) if config.debug else "Something went wrong"
        }
    )

if __name__ == "__main__":
    uvicorn.run(
        "innocore_ai.api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=config.debug,
        log_level="info"
    )
