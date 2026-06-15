"""学生端API接口.

提供学生登录、代码提交、获取评分等功能.
"""

from fastapi import APIRouter, HTTPException, status
from typing import Optional

from app.models.schemas import (
    StudentLogin, CodeSubmit, ApiResponse, 
    AIScoreResult, SubmissionRecord
)
from app.models.database import (
    save_submission, get_submission, get_tasks
)
from app.core.ai_grader import grade_code
from app.core.code_runner import run_code
from app.utils.logger import get_logger
from app.utils.security import validate_student_id, validate_code
from pydantic import BaseModel, Field

logger = get_logger(__name__)
router = APIRouter(prefix="/student")


@router.post("/login", response_model=ApiResponse)
async def login(data: StudentLogin):
    """学生登录.

    验证学生信息并返回登录凭证.
    """
    if not validate_student_id(data.student_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="学号格式错误，应为8-12位数字"
        )

    logger.info(f"学生登录: {data.student_id} - {data.student_name}")

    return ApiResponse(
        code=200,
        message="登录成功",
        data={
            "student_id": data.student_id,
            "student_name": data.student_name,
            "course": data.course
        }
    )


class CodeRunRequest(BaseModel):
    """代码运行请求."""
    code: str = Field(..., max_length=10000, description="代码")
    language: str = Field(..., pattern=r"^(cpp|c|java|python|python3)$", description="编程语言")
    stdin: str = Field(default="", max_length=1000, description="标准输入")


@router.post("/run")
async def run_my_code(data: CodeRunRequest):
    """编译并运行代码.

    返回编译错误、运行时输出和退出码.
    """
    logger.info(f"代码运行: lang={data.language}, code_len={len(data.code)}")

    result = run_code(data.code, data.language, data.stdin)

    return ApiResponse(
        code=200,
        message="运行完成" if result["success"] else "运行出错",
        data=result
    )


@router.post("/submit", response_model=ApiResponse)
async def submit_code(data: CodeSubmit):
    """提交代码.

    保存代码并触发AI评分.
    """
    # 验证学号
    if not validate_student_id(data.student_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="学号格式错误"
        )

    # 验证代码
    is_valid, error_msg = validate_code(data.code)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_msg
        )

    logger.info(f"代码提交: student={data.student_id}, task={data.task_id}, lang={data.language}")

    # AI评分
    ai_result = await grade_code(data.code, data.language)

    # 保存到数据库
    save_submission(
        student_id=data.student_id,
        student_name=data.student_name,
        course=data.course,
        task_id=data.task_id,
        language=data.language,
        code=data.code,
        ai_score=ai_result
    )

    return ApiResponse(
        code=200,
        message="提交成功",
        data={
            "student_id": data.student_id,
            "task_id": data.task_id,
            "ai_score": ai_result
        }
    )


@router.get("/submission", response_model=ApiResponse)
async def get_my_submission(student_id: str, task_id: str):
    """获取我的提交记录.

    Args:
        student_id: 学号
        task_id: 任务ID
    """
    if not validate_student_id(student_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="学号格式错误"
        )

    submission = get_submission(student_id, task_id)

    if not submission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="未找到提交记录"
        )

    return ApiResponse(
        code=200,
        message="查询成功",
        data=submission
    )


@router.get("/tasks", response_model=ApiResponse)
async def list_tasks(course: Optional[str] = None):
    """获取任务列表.

    Args:
        course: 可选，按课程筛选
    """
    tasks = get_tasks()

    if course:
        tasks = [t for t in tasks if t["course"] == course]

    return ApiResponse(
        code=200,
        message="查询成功",
        data=tasks
    )
