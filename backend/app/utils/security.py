"""安全工具模块.

提供输入验证、敏感信息过滤等安全功能.
"""

import re
from typing import List, Optional

# 危险代码模式（用于学生代码提交检查）
DANGEROUS_PATTERNS = [
    r"import\s+os",
    r"import\s+subprocess",
    r"subprocess",
    r"eval\s*\(",
    r"exec\s*\(",
    r"__import__",
    r"system\s*\(",
    r"popen\s*\(",
    r"open\s*\(",  # 文件操作
    r"socket",
    r"urllib",
    r"requests",
    r"ftplib",
    r"telnetlib",
]

# SQL注入关键词
SQL_INJECTION_KEYWORDS = [
    "DROP", "DELETE", "INSERT", "UPDATE", "ALTER",
    "EXEC", "EXECUTE", "UNION", "SELECT", "FROM",
    "WHERE", "OR", "AND", "--", "/*", "*/"
]


def validate_student_id(student_id: str) -> bool:
    """验证学号/用户名格式."""
    if not student_id:
        return False
    return bool(re.match(r"^[a-zA-Z0-9_]{4,30}$", student_id))


def validate_code(code: str, max_length: int = 10000) -> tuple[bool, Optional[str]]:
    """验证学生提交的代码.

    检查代码长度和危险操作.

    Args:
        code: 代码内容
        max_length: 最大允许长度

    Returns:
        (是否有效, 错误信息)
    """
    if not code or not code.strip():
        return False, "代码不能为空"

    if len(code) > max_length:
        return False, f"代码长度超过限制（最大{max_length}字符）"

    # 检查危险代码
    for pattern in DANGEROUS_PATTERNS:
        if re.search(pattern, code, re.IGNORECASE):
            return False, f"代码包含危险操作，请删除: {pattern}"

    return True, None


def sanitize_filename(filename: str) -> str:
    """清理文件名，防止路径遍历攻击.

    Args:
        filename: 原始文件名

    Returns:
        安全的文件名
    """
    # 移除路径分隔符和危险字符
    filename = re.sub(r'[\/:*?"<>|]', "_", filename)
    filename = filename.strip(".")
    return filename or "unnamed"


def mask_sensitive_data(data: str, visible_chars: int = 4) -> str:
    """脱敏处理敏感数据.

    Args:
        data: 原始数据
        visible_chars: 保留可见字符数

    Returns:
        脱敏后的数据，如 sk-****abcd
    """
    if len(data) <= visible_chars * 2:
        return "*" * len(data)
    return data[:visible_chars] + "****" + data[-visible_chars:]
