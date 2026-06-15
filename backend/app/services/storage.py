"""文件存储服务.

处理代码文件的临时存储和清理.
"""

import shutil
from pathlib import Path
from typing import Optional
from datetime import datetime, timedelta

from app.config import SUBMISSIONS_DIR, JPLAG_RESULTS_DIR, EXPORTS_DIR
from app.utils.logger import get_logger

logger = get_logger(__name__)


def cleanup_old_files(max_age_days: int = 7) -> dict:
    """清理过期文件.

    Args:
        max_age_days: 文件最大保留天数

    Returns:
        清理统计
    """
    cutoff = datetime.now() - timedelta(days=max_age_days)
    stats = {"deleted": 0, "errors": 0}

    for directory in [SUBMISSIONS_DIR, JPLAG_RESULTS_DIR, EXPORTS_DIR]:
        for item in directory.iterdir():
            try:
                # 检查修改时间
                mtime = datetime.fromtimestamp(item.stat().st_mtime)
                if mtime < cutoff:
                    if item.is_dir():
                        shutil.rmtree(item)
                    else:
                        item.unlink()
                    stats["deleted"] += 1
                    logger.info(f"清理过期文件: {item}")
            except Exception as e:
                stats["errors"] += 1
                logger.warning(f"清理失败 {item}: {str(e)}")

    return stats


def get_disk_usage() -> dict:
    """获取存储使用情况.

    Returns:
        各目录使用统计
    """
    result = {}

    for name, directory in [
        ("submissions", SUBMISSIONS_DIR),
        ("jplag_results", JPLAG_RESULTS_DIR),
        ("exports", EXPORTS_DIR)
    ]:
        total_size = 0
        file_count = 0

        for item in directory.rglob("*"):
            if item.is_file():
                total_size += item.stat().st_size
                file_count += 1

        result[name] = {
            "file_count": file_count,
            "total_size_mb": round(total_size / (1024 * 1024), 2)
        }

    return result
