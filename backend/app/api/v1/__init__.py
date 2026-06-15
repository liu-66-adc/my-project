"""API v1 路由模块.
"""

from fastapi import APIRouter

from app.api.v1 import student, teacher, auth

router = APIRouter(prefix="/api/v1")

router.include_router(auth.router, tags=["认证"])
router.include_router(student.router, tags=["学生端"])
router.include_router(teacher.router, tags=["教师端"])
