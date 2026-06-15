"""FastAPI应用主入口.

配置应用、注册路由、初始化数据库.
"""
from dotenv import load_dotenv
import os

# 加载当前目录的 .env 文件
load_dotenv()

# 如果上面的不行，试试指定路径
# load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.config import (
    APP_NAME, APP_VERSION, DEBUG, ALLOWED_ORIGINS,
    validate_config
)
from app.models.database import init_db
from app.api.v1 import router as api_v1_router
from app.utils.logger import get_logger

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理.

    启动时初始化数据库，关闭时清理资源.
    """
    # 启动
    logger.info(f"🚀 {APP_NAME} v{APP_VERSION} 启动中...")

    # 验证配置
    errors = validate_config()
    if errors:
        for error in errors:
            logger.warning(f"配置警告: {error}")

    # 初始化数据库
    init_db()

    yield

    # 关闭
    logger.info("👋 应用关闭")


# 创建应用
app = FastAPI(
    title=APP_NAME,
    version=APP_VERSION,
    description="模仿学习通AI实践的代码教学平台，支持AI自动评分和JPlag代码查重",
    docs_url="/docs" if DEBUG else None,
    redoc_url="/redoc" if DEBUG else None,
    lifespan=lifespan
)

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 请求中间件
@app.middleware("http")
async def add_request_metadata(request: Request, call_next):
    """为每个请求添加元数据.

    包括请求ID、处理时间等.
    """
    request_id = str(uuid.uuid4())[:8]
    request.state.request_id = request_id

    start_time = time.time()

    logger.info(
        f"请求开始: {request.method} {request.url.path} | request_id={request_id}"
    )

    response = await call_next(request)

    process_time = time.time() - start_time
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Process-Time"] = str(round(process_time, 3))

    logger.info(
        f"请求完成: {request.method} {request.url.path} | "
        f"status={response.status_code} | time={process_time:.3f}s | request_id={request_id}"
    )

    return response


# 异常处理
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """全局异常处理.

    捕获未处理的异常，返回统一错误格式.
    """
    request_id = getattr(request.state, "request_id", "unknown")

    logger.error(
        f"未处理异常: {str(exc)} | request_id={request_id}",
        exc_info=True
    )

    return JSONResponse(
        status_code=500,
        content={
            "code": 500,
            "message": "服务器内部错误",
            "data": None,
            "timestamp": time.time(),
            "request_id": request_id
        }
    )


# 注册路由
app.include_router(api_v1_router)


# 前端静态文件
from pathlib import Path
from fastapi.responses import FileResponse, HTMLResponse
frontend_dir = Path(__file__).parent.parent.parent / "frontend"


@app.get("/")
async def root():
    """根路径，返回学生登录页."""
    return FileResponse(str(frontend_dir / "index.html"), media_type="text/html")


@app.get("/editor.html")
async def editor_page():
    """代码编辑页面."""
    return FileResponse(str(frontend_dir / "editor.html"), media_type="text/html")


@app.get("/teacher.html")
async def teacher_page():
    """教师看板页面."""
    return FileResponse(str(frontend_dir / "teacher.html"), media_type="text/html")


@app.get("/teacher-login.html")
async def teacher_login_page():
    """教师登录页面."""
    return FileResponse(str(frontend_dir / "teacher-login.html"), media_type="text/html")


# 健康检查
@app.get("/health")
async def health_check():
    """健康检查接口."""
    return {
        "status": "healthy",
        "timestamp": time.time()
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=DEBUG,
        log_level="info"
    )
