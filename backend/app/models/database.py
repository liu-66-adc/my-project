"""数据库操作模块.

使用SQLite作为数据库，支持异步操作.
"""

import sqlite3
import json
import uuid
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any
from contextlib import contextmanager

from app.config import DATABASE_URL
from app.utils.logger import get_logger

logger = get_logger(__name__)

# 解析数据库路径
def _get_db_path() -> Path:
    """从DATABASE_URL解析数据库文件路径."""
    if DATABASE_URL.startswith("sqlite:///"):
        return Path(DATABASE_URL.replace("sqlite:///", ""))
    return Path(DATABASE_URL)


DB_PATH = _get_db_path()


def init_db() -> None:
    """初始化数据库表结构."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    with _get_connection() as conn:
        cursor = conn.cursor()

        # 用户表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL CHECK(role IN ('teacher', 'student')),
                student_name TEXT DEFAULT '',
                course TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 创建默认教师账号（admin / admin123）
        cursor.execute("SELECT COUNT(*) FROM users WHERE role='teacher'")
        if cursor.fetchone()[0] == 0:
            from app.core.auth import hash_password
            cursor.execute(
                "INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)",
                ("admin", hash_password("admin123"), "teacher")
            )
            logger.info("已创建默认教师账号: admin / admin123")

        # 提交记录表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS submissions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id TEXT NOT NULL,
                student_name TEXT NOT NULL,
                course TEXT NOT NULL,
                task_id TEXT NOT NULL,
                language TEXT NOT NULL,
                code TEXT NOT NULL,
                ai_score TEXT,
                plagiarism_max REAL DEFAULT 0,
                plagiarism_with TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(student_id, task_id)
            )
        """)

        # 任务表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id TEXT NOT NULL UNIQUE,
                course TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT,
                language TEXT DEFAULT 'cpp',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 插入示例任务
        cursor.execute("""
            INSERT OR IGNORE INTO tasks (task_id, course, title, description, language)
            VALUES 
                ('task-001', '数据结构2026', '最短路径实现', '实现Dijkstra算法，求解带权有向图的单源最短路径', 'cpp'),
                ('task-002', '数据结构2026', '排序算法实现', '实现快速排序和归并排序，比较性能', 'cpp'),
                ('task-003', '算法设计2026', '二叉树遍历', '实现前序、中序、后序遍历算法', 'cpp')
        """)

        conn.commit()
        logger.info("数据库初始化完成")


@contextmanager
def _get_connection():
    """获取数据库连接的上下文管理器."""
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def save_submission(
    student_id: str,
    student_name: str,
    course: str,
    task_id: str,
    language: str,
    code: str,
    ai_score: Optional[Dict] = None
) -> None:
    """保存或更新提交记录.

    使用INSERT OR REPLACE实现upsert操作.
    """
    with _get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO submissions 
            (student_id, student_name, course, task_id, language, code, ai_score)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(student_id, task_id) DO UPDATE SET
                student_name = excluded.student_name,
                course = excluded.course,
                language = excluded.language,
                code = excluded.code,
                ai_score = excluded.ai_score,
                updated_at = CURRENT_TIMESTAMP
        """, (
            student_id, student_name, course, task_id, language, code,
            json.dumps(ai_score, ensure_ascii=False) if ai_score else None
        ))
        conn.commit()
        logger.info(f"保存提交记录: student_id={student_id}, task_id={task_id}")


def get_submission(student_id: str, task_id: str) -> Optional[Dict[str, Any]]:
    """获取单个提交记录."""
    with _get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT student_id, student_name, course, task_id, language,
                   code, ai_score, plagiarism_max, plagiarism_with, created_at
            FROM submissions WHERE student_id = ? AND task_id = ?
        """, (student_id, task_id))

        row = cursor.fetchone()
        if not row:
            return None

        return _row_to_dict(row)


def get_all_submissions(
    task_id: Optional[str] = None,
    course: Optional[str] = None
) -> List[Dict[str, Any]]:
    """获取所有提交记录，支持筛选."""
    with _get_connection() as conn:
        cursor = conn.cursor()
        query = """
            SELECT student_id, student_name, course, task_id, language,
                   code, ai_score, plagiarism_max, plagiarism_with, created_at
            FROM submissions WHERE 1=1
        """
        params = []

        if task_id:
            query += " AND task_id = ?"
            params.append(task_id)
        if course:
            query += " AND course = ?"
            params.append(course)

        query += " ORDER BY created_at DESC"

        cursor.execute(query, params)
        rows = cursor.fetchall()

        return [_row_to_dict(row) for row in rows]


def update_plagiarism(
    student_id: str,
    task_id: str,
    max_similarity: float,
    with_student: str
) -> None:
    """更新查重结果."""
    with _get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE submissions 
            SET plagiarism_max = ?, plagiarism_with = ?
            WHERE student_id = ? AND task_id = ?
        """, (max_similarity, with_student, student_id, task_id))
        conn.commit()


def get_tasks() -> List[Dict[str, Any]]:
    """获取所有任务列表."""
    with _get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT t.task_id, t.course, t.title, t.description, t.language,
                   COUNT(s.student_id) as total_submissions
            FROM tasks t
            LEFT JOIN submissions s ON t.task_id = s.task_id
            GROUP BY t.task_id
            ORDER BY t.created_at DESC
        """)
        rows = cursor.fetchall()

        return [
            {
                "task_id": row["task_id"],
                "course": row["course"],
                "title": row["title"],
                "description": row["description"],
                "language": row["language"],
                "total_submissions": row["total_submissions"]
            }
            for row in rows
        ]


def get_task_stats(task_id: str) -> Dict[str, Any]:
    """获取任务统计信息."""
    with _get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                COUNT(*) as total,
                AVG(CASE WHEN ai_score IS NOT NULL THEN 
                    json_extract(ai_score, '$.total_score') END) as avg_score,
                MAX(plagiarism_max) as max_plagiarism
            FROM submissions WHERE task_id = ?
        """, (task_id,))

        row = cursor.fetchone()
        return {
            "total_submissions": row["total"] or 0,
            "avg_score": round(row["avg_score"] or 0, 1),
            "max_plagiarism": row["max_plagiarism"] or 0
        }


# ========== 用户管理 ==========


def create_user(username: str, password_hash: str, role: str,
                student_name: str = "", course: str = "") -> Optional[int]:
    """创建用户，返回用户ID."""
    try:
        with _get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO users (username, password_hash, role, student_name, course)
                   VALUES (?, ?, ?, ?, ?)""",
                (username, password_hash, role, student_name, course)
            )
            conn.commit()
            return cursor.lastrowid
    except sqlite3.IntegrityError:
        logger.warning(f"用户名已存在: {username}")
        return None


def get_user(username: str) -> Optional[Dict[str, Any]]:
    """通过用户名获取用户."""
    with _get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, username, password_hash, role, student_name, course, created_at "
            "FROM users WHERE username = ?", (username,)
        )
        row = cursor.fetchone()
        if row:
            return dict(row)
        return None


def get_students() -> List[Dict[str, Any]]:
    """获取所有学生账号."""
    with _get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, username, student_name, course, created_at "
            "FROM users WHERE role = 'student' ORDER BY created_at DESC"
        )
        return [dict(r) for r in cursor.fetchall()]


def delete_user(user_id: int) -> bool:
    """删除用户."""
    with _get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM users WHERE id = ? AND role = 'student'", (user_id,))
        conn.commit()
        return cursor.rowcount > 0


def _row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
    """将数据库行转换为字典."""
    result = dict(row)
    if result.get("ai_score"):
        try:
            result["ai_score"] = json.loads(result["ai_score"])
        except json.JSONDecodeError:
            result["ai_score"] = None
    return result
