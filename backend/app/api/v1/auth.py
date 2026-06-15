"""认证与用户管理 API.

教师登录、学生账号 CRUD.
"""
from fastapi import APIRouter, HTTPException, status, Request
from pydantic import BaseModel, Field

from app.core.auth import hash_password, verify_password, create_token, verify_token
from app.models.database import create_user, get_user, get_students, delete_user
from app.models.schemas import ApiResponse
from app.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/auth")


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=2, max_length=50)
    password: str = Field(..., min_length=4, max_length=100)


class StudentCreateRequest(BaseModel):
    username: str = Field(..., min_length=4, max_length=50, description="学生登录账号")
    password: str = Field(..., min_length=4, max_length=100, description="密码")
    student_name: str = Field(..., min_length=1, max_length=20, description="学生姓名")
    course: str = Field(default="", max_length=50, description="课程")


@router.post("/login")
async def login(data: LoginRequest):
    """教师/学生登录，返回 JWT 令牌."""
    user = get_user(data.username)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户名或密码错误")

    if not verify_password(data.password, user["password_hash"]):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户名或密码错误")

    token = create_token(str(user["id"]), user["role"], user["username"])

    return ApiResponse(code=200, message="登录成功", data={
        "token": token,
        "role": user["role"],
        "username": user["username"],
        "student_name": user.get("student_name", ""),
        "course": user.get("course", "")
    })


@router.post("/verify")
@router.get("/verify")
async def verify(request: Request):
    """验证令牌是否有效."""
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="缺少令牌")

    payload = verify_token(auth_header[7:])
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="令牌无效")

    return ApiResponse(code=200, message="令牌有效", data=payload)


@router.post("/students/create")
async def create_student(data: StudentCreateRequest, request: Request):
    """教师创建学生账号（需要教师权限）."""
    # 验证权限
    auth = _require_teacher(request)
    if not auth:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="仅教师可操作")

    existing = get_user(data.username)
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="账号已存在")

    user_id = create_user(
        username=data.username,
        password_hash=hash_password(data.password),
        role="student",
        student_name=data.student_name,
        course=data.course
    )

    if not user_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="创建失败，账号可能已存在")

    logger.info(f"教师创建学生账号: {data.username} ({data.student_name})")
    return ApiResponse(code=200, message="创建成功", data={"user_id": user_id})


@router.get("/students/list")
async def list_students(request: Request):
    """获取所有学生账号（需要教师权限）."""
    if not _require_teacher(request):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="仅教师可操作")

    students = get_students()
    return ApiResponse(code=200, message="查询成功", data=students)


@router.post("/students/delete")
async def remove_student(user_id: int, request: Request):
    """删除学生账号."""
    if not _require_teacher(request):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="仅教师可操作")

    ok = delete_user(user_id)
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="学生不存在")

    return ApiResponse(code=200, message="删除成功")


def _require_teacher(request: Request) -> bool:
    """检查请求是否来自教师."""
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return False
    payload = verify_token(auth_header[7:])
    if not payload or payload.get("role") != "teacher":
        return False
    request.state.user = payload
    return True
