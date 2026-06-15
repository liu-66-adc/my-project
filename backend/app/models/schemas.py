"""Pydantic数据模型定义.

定义所有API请求和响应的数据结构.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, validator


class StudentLogin(BaseModel):
    """学生登录请求."""
    student_id: str = Field(..., min_length=8, max_length=12, description="学号")
    student_name: str = Field(..., min_length=2, max_length=20, description="姓名")
    course: str = Field(..., min_length=1, max_length=50, description="课程名称")

    class Config:
        json_schema_extra = {
            "example": {
                "student_id": "20231234",
                "student_name": "张三",
                "course": "数据结构2026"
            }
        }


class CodeSubmit(BaseModel):
    """代码提交请求."""
    student_id: str = Field(..., description="学号")
    student_name: str = Field(..., description="姓名")
    course: str = Field(..., description="课程")
    task_id: str = Field(..., min_length=1, max_length=50, description="任务ID")
    language: str = Field(..., pattern=r"^(cpp|c|java|python|python3)$", description="编程语言")
    code: str = Field(..., max_length=10000, description="代码内容")


class AIScoreDetail(BaseModel):
    """AI评分单项详情."""
    category: str = Field(..., description="评分维度")
    score: int = Field(..., ge=0, description="得分")
    max_score: int = Field(..., gt=0, description="满分")
    comment: str = Field(..., description="评语")


class AIScoreResult(BaseModel):
    """AI评分结果."""
    total_score: int = Field(..., ge=0, le=100, description="总分")
    details: List[AIScoreDetail] = Field(..., description="各维度得分详情")
    problems: List[str] = Field(default=[], description="存在的问题")
    suggestions: str = Field(default="", description="改进建议")


class PlagiarismPair(BaseModel):
    """查重对比结果."""
    student_a: str = Field(..., description="学生A学号")
    student_b: str = Field(..., description="学生B学号")
    similarity: float = Field(..., ge=0, le=100, description="相似度百分比")
    matched_lines: int = Field(..., ge=0, description="匹配行数")


class PlagiarismReport(BaseModel):
    """查重报告."""
    task_id: str = Field(..., description="任务ID")
    total_submissions: int = Field(..., ge=0, description="总提交数")
    comparisons: List[PlagiarismPair] = Field(default=[], description="对比结果")
    max_similarity: Dict[str, Dict[str, Any]] = Field(default={}, description="每学生最高相似度")


class SubmissionRecord(BaseModel):
    """提交记录."""
    student_id: str
    student_name: str
    course: str
    task_id: str
    language: str
    code: str
    ai_score: Optional[AIScoreResult] = None
    plagiarism_max: float = 0.0
    plagiarism_with: str = ""
    created_at: str


class ApiResponse(BaseModel):
    """统一API响应格式."""
    code: int = Field(200, description="状态码")
    message: str = Field("success", description="消息")
    data: Optional[Any] = Field(None, description="数据")
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
    request_id: str = Field("", description="请求ID")


class TaskInfo(BaseModel):
    """任务信息."""
    task_id: str
    course: str
    total_submissions: int = 0
    avg_score: float = 0.0
