"""应用配置模块.

所有配置从环境变量读取，遵循12-Factor App原则.
"""

import os
from pathlib import Path
from typing import Optional

# 项目根目录
BASE_DIR = Path(__file__).parent.parent.parent

# 数据目录
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

# 数据库
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DATA_DIR}/database.sqlite")

# AI评分API
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_API_URL = os.getenv("DEEPSEEK_API_URL", "https://api.deepseek.com/chat/completions")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

# JPlag
JPLAG_JAR_PATH = os.getenv("JPLAG_JAR_PATH", str(BASE_DIR / "jplag-5.1.0.jar"))
SUBMISSIONS_DIR = BASE_DIR / "submissions"
JPLAG_RESULTS_DIR = BASE_DIR / "jplag-results"
EXPORTS_DIR = BASE_DIR / "exports"

# 确保目录存在
for d in [SUBMISSIONS_DIR, JPLAG_RESULTS_DIR, EXPORTS_DIR]:
    d.mkdir(exist_ok=True)

# 应用设置
APP_NAME = os.getenv("APP_NAME", "代码实践平台")
APP_VERSION = os.getenv("APP_VERSION", "1.0.0")
DEBUG = os.getenv("DEBUG", "false").lower() == "true"

# 安全设置
MAX_CODE_LENGTH = int(os.getenv("MAX_CODE_LENGTH", "10000"))
MAX_REQUEST_SIZE = int(os.getenv("MAX_REQUEST_SIZE", "10485760"))  # 10MB
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*").split(",")

# 日志
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_DIR = BASE_DIR / "backend" / "logs"
LOG_DIR.mkdir(exist_ok=True)


def validate_config() -> list[str]:
    """验证配置是否完整，返回错误列表."""
    errors = []

    if not DEEPSEEK_API_KEY or DEEPSEEK_API_KEY == "sk-xxxxxxxxxxxxxxxxxxxxxxxx":
        errors.append("DEEPSEEK_API_KEY 未设置，请配置环境变量或在 .env 文件中设置")

    if not Path(JPLAG_JAR_PATH).exists():
        errors.append(f"JPlag JAR 文件未找到: {JPLAG_JAR_PATH}，请下载并放置到项目根目录")

    return errors
