"""日志配置模块.

提供统一的日志格式和输出方式.
"""

import logging
import sys
from pathlib import Path
from datetime import datetime

from app.config import LOG_LEVEL, LOG_DIR


def get_logger(name: str) -> logging.Logger:
    """获取配置好的日志记录器.

    Args:
        name: 日志记录器名称，通常使用 __name__

    Returns:
        配置好的Logger实例
    """
    logger = logging.getLogger(name)

    # 避免重复添加handler
    if logger.handlers:
        return logger

    logger.setLevel(getattr(logging, LOG_LEVEL.upper()))

    # 控制台输出
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)

    # 文件输出
    log_file = LOG_DIR / f"app_{datetime.now().strftime('%Y%m%d')}.log"
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)

    # 统一格式
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    console_handler.setFormatter(formatter)
    file_handler.setFormatter(formatter)

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    return logger
