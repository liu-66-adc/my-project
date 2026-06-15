"""教师端API接口.

提供成绩查询、查重检测、数据导出等功能.
"""

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import FileResponse
from typing import Optional
from datetime import datetime
import pandas as pd

from app.models.schemas import ApiResponse, PlagiarismReport
from app.models.database import (
    get_all_submissions, get_tasks, get_task_stats, update_plagiarism
)
from app.core.plagiarism import run_plagiarism_check
from app.config import EXPORTS_DIR
from app.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/teacher")


@router.get("/submissions", response_model=ApiResponse)
async def list_submissions(
    task_id: Optional[str] = None,
    course: Optional[str] = None
):
    """获取所有提交记录.

    Args:
        task_id: 可选，按任务筛选
        course: 可选，按课程筛选
    """
    submissions = get_all_submissions(task_id=task_id, course=course)

    return ApiResponse(
        code=200,
        message="查询成功",
        data={
            "total": len(submissions),
            "submissions": submissions
        }
    )


@router.get("/tasks", response_model=ApiResponse)
async def list_tasks():
    """获取所有任务列表."""
    tasks = get_tasks()

    return ApiResponse(
        code=200,
        message="查询成功",
        data=tasks
    )


@router.get("/tasks/{task_id}/stats", response_model=ApiResponse)
async def task_stats(task_id: str):
    """获取任务统计信息.

    Args:
        task_id: 任务ID
    """
    stats = get_task_stats(task_id)

    return ApiResponse(
        code=200,
        message="查询成功",
        data=stats
    )


@router.post("/plagiarism/check", response_model=ApiResponse)
async def check_plagiarism(task_id: str, language: str = "cpp"):
    """运行查重检测.

    Args:
        task_id: 任务ID
        language: 编程语言，默认cpp
    """
    logger.info(f"启动查重: task_id={task_id}, language={language}")

    result = run_plagiarism_check(task_id, language)

    if "error" in result:
        logger.error(f"查重失败: {result['error']}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=result["error"]
        )

    logger.info(f"查重完成: {result['total_submissions']} 份提交")

    return ApiResponse(
        code=200,
        message=f"查重完成，共 {result['total_submissions']} 份提交",
        data=result
    )


@router.get("/export/grades")
async def export_grades(task_id: str):
    """导出成绩Excel.

    Args:
        task_id: 任务ID
    """
    submissions = get_all_submissions(task_id=task_id)

    if not submissions:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="该任务暂无提交记录"
        )

    # 构建DataFrame
    rows = []
    for s in submissions:
        ai = s.get("ai_score", {}) or {}
        details = ai.get("details", [])

        def get_score(category: str) -> int:
            item = next((d for d in details if d.get("category") == category), None)
            return item.get("score", 0) if item else 0

        rows.append({
            "学号": s["student_id"],
            "姓名": s["student_name"],
            "课程": s["course"],
            "任务": s["task_id"],
            "语言": s["language"],
            "总分": ai.get("total_score", 0),
            "功能正确性": get_score("功能正确性"),
            "代码规范": get_score("代码规范"),
            "算法效率": get_score("算法效率"),
            "代码结构": get_score("代码结构"),
            "查重率(%)": s.get("plagiarism_max", 0),
            "最相似对象": s.get("plagiarism_with", ""),
            "提交时间": s["created_at"]
        })

    df = pd.DataFrame(rows)

    # 生成文件名
    filename = f"成绩_{task_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    filepath = EXPORTS_DIR / filename

    # 写入Excel
    with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='成绩明细', index=False)

        # 添加统计sheet
        stats_data = {
            "指标": ["总人数", "平均分", "最高分", "最低分", "疑似抄袭人数(>50%)"],
            "数值": [
                len(rows),
                round(df["总分"].mean(), 1),
                df["总分"].max(),
                df["总分"].min(),
                len(df[df["查重率(%)"] > 50])
            ]
        }
        pd.DataFrame(stats_data).to_excel(writer, sheet_name='统计汇总', index=False)

    logger.info(f"成绩导出: {filename}")

    return FileResponse(
        filepath,
        filename=filename,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
