"""代码查重引擎模块.

支持 JPlag（Java）和内置 Python 查重引擎.
"""

import json
import shutil
import re
import sqlite3
from pathlib import Path
from typing import Dict, Any, List, Tuple, Set

from app.config import JPLAG_JAR_PATH, SUBMISSIONS_DIR, JPLAG_RESULTS_DIR
from app.models.database import update_plagiarism, DB_PATH
from app.utils.logger import get_logger

logger = get_logger(__name__)


# ============================================================
# 内置 Python 查重引擎（纯 Python，零外部依赖）
# ============================================================

def _tokenize_code(code: str, language: str) -> List[str]:
    """将代码分词，去除注释和字符串内容."""
    # 去除注释
    if language in ("cpp", "c", "java"):
        # 去除单行注释
        code = re.sub(r'//.*', '', code)
        # 去除多行注释
        code = re.sub(r'/\*.*?\*/', '', code, flags=re.DOTALL)
    elif language in ("python", "python3"):
        code = re.sub(r'#.*', '', code)
        code = re.sub(r'""".*?"""', '', code, flags=re.DOTALL)
        code = re.sub(r"'''.*?'''", '', code, flags=re.DOTALL)

    # 去除字符串字面量
    code = re.sub(r'"[^"]*"', '', code)
    code = re.sub(r"'[^']*'", '', code)

    # 分词：提取标识符、关键字、运算符
    tokens = re.findall(r'[a-zA-Z_]\w*|[{}();,=+\-*/<>!&|^~%\[\]?:.]|[0-9]+', code)

    # 将用户定义的标识符归一化（变量名、函数名 → 通用标记）
    # 保留关键字原样，其他标识符替换为通用标记
    keywords = {
        'if', 'else', 'for', 'while', 'do', 'switch', 'case', 'break',
        'continue', 'return', 'int', 'float', 'double', 'char', 'void',
        'long', 'short', 'unsigned', 'signed', 'const', 'static', 'struct',
        'class', 'public', 'private', 'protected', 'virtual', 'using',
        'namespace', 'include', 'template', 'typename', 'auto', 'def',
        'import', 'from', 'and', 'or', 'not', 'in', 'is', 'lambda',
        'try', 'except', 'finally', 'raise', 'with', 'as', 'yield',
        'print', 'range', 'len', 'map', 'filter', 'sorted', 'enumerate',
        'zip', 'list', 'dict', 'set', 'str', 'int', 'float', 'bool',
        'True', 'False', 'None', 'new', 'delete', 'this', 'virtual',
        'override', 'final', 'default', 'nullptr', 'NULL', 'size_t',
        'vector', 'queue', 'stack', 'priority_queue', 'pair', 'make_pair',
        'cin', 'cout', 'endl', 'string', 'main', 'std', 'max', 'min',
        'abs', 'swap', 'sort', 'begin', 'end', 'push_back', 'pop_back',
        'push', 'pop', 'top', 'front', 'back', 'empty', 'size', 'clear',
        'first', 'second', 'greater', 'less', 'true', 'false',
    }

    normalized = []
    for t in tokens:
        if t in keywords or not t.isidentifier():
            normalized.append(t)
        else:
            # 用户定义的标识符全部归一化
            normalized.append('_ID_')

    return normalized


def _get_ngrams(tokens: List[str], n: int = 8) -> Set[Tuple[str, ...]]:
    """生成 n-gram 集合."""
    if len(tokens) < n:
        return {tuple(tokens)}
    return set(tuple(tokens[i:i+n]) for i in range(len(tokens) - n + 1))


def _calc_similarity(tokens_a: List[str], tokens_b: List[str]) -> float:
    """计算两段代码的相似度（基于 n-gram Jaccard 系数）."""
    ngrams_a = _get_ngrams(tokens_a)
    ngrams_b = _get_ngrams(tokens_b)

    if not ngrams_a or not ngrams_b:
        return 0.0

    intersection = ngrams_a & ngrams_b
    union = ngrams_a | ngrams_b

    return round(len(intersection) / len(union) * 100, 1)


def _python_plagiarism_check(task_id: str, language: str) -> Dict[str, Any]:
    """纯 Python 代码查重."""
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT student_id, student_name, code FROM submissions WHERE task_id = ?",
        (task_id,)
    )
    rows = cursor.fetchall()
    conn.close()

    if len(rows) < 2:
        return {"error": "需要至少2份提交才能进行查重"}

    # 分词预处理
    tokenized = []
    for sid, sname, code in rows:
        tokens = _tokenize_code(code, language)
        tokenized.append((sid, sname, tokens))

    # 两两比较
    comparisons = []
    max_similarity = {}

    for i in range(len(tokenized)):
        for j in range(i+1, len(tokenized)):
            sid_a, name_a, tokens_a = tokenized[i]
            sid_b, name_b, tokens_b = tokenized[j]

            sim = _calc_similarity(tokens_a, tokens_b)

            comparisons.append({
                "student_a": sid_a,
                "student_b": sid_b,
                "similarity": sim,
                "matched_lines": int(sim * len(tokens_a) / 100)
            })

            # 更新最高相似度
            for sid, other_sid, val in [(sid_a, sid_b, sim), (sid_b, sid_a, sim)]:
                if sid not in max_similarity or val > max_similarity[sid]["value"]:
                    max_similarity[sid] = {
                        "value": val,
                        "with": other_sid
                    }

    # 更新数据库
    for student_id, data in max_similarity.items():
        try:
            update_plagiarism(student_id, task_id, data["value"], data["with"])
        except Exception as e:
            logger.error(f"更新查重记录失败: {e}")

    logger.info(f"Python查重完成: {len(comparisons)} 组对比")

    return {
        "task_id": task_id,
        "total_submissions": len(rows),
        "comparisons": comparisons,
        "max_similarity": max_similarity,
        "engine": "python-builtin"
    }


# ============================================================
# JPlag 集成（备用，需要 Java + jar）
# ============================================================

LANGUAGE_MAP = {"cpp": "cpp", "c": "c", "java": "java", "python": "python3", "python3": "python3"}
EXTENSION_MAP = {"cpp": ".cpp", "c": ".c", "java": ".java", "python": ".py", "python3": ".py"}


def check_jplag_available() -> Tuple[bool, str]:
    """检查JPlag是否可用."""
    jar_path = Path(JPLAG_JAR_PATH)
    if not jar_path.exists():
        return False, f"JPlag JAR 未找到"

    try:
        import subprocess
        result = subprocess.run(["java", "-version"], capture_output=True, timeout=5)
        if result.returncode != 0:
            return False, "Java 环境未配置"
    except Exception:
        return False, "Java 不可用"

    return True, ""


def run_plagiarism_check(task_id: str, language: str = "cpp") -> Dict[str, Any]:
    """运行查重检测.

    优先使用 JPlag（Java），不可用时降级到 Python 内置引擎.
    """
    available, _ = check_jplag_available()

    if available:
        result = _jplag_check(task_id, language)
        if "error" not in result:
            return result
        logger.warning(f"JPlag 查重失败，降级到 Python 引擎: {result['error']}")

    # 降级到 Python 引擎
    logger.info("使用 Python 内置查重引擎")
    return _python_plagiarism_check(task_id, language)


def _jplag_check(task_id: str, language: str) -> Dict[str, Any]:
    """JPlag 查重."""
    import subprocess
    import zipfile

    task_dir = SUBMISSIONS_DIR / task_id
    task_dir.mkdir(parents=True, exist_ok=True)
    for item in task_dir.iterdir():
        if item.is_dir():
            shutil.rmtree(item)
        else:
            item.unlink()

    # 从数据库读取代码
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("SELECT student_id, code FROM submissions WHERE task_id = ?", (task_id,))
    rows = cursor.fetchall()
    conn.close()

    ext = EXTENSION_MAP.get(language, ".txt")
    for student_id, code in rows:
        student_dir = task_dir / student_id
        student_dir.mkdir(exist_ok=True)
        with open(student_dir / f"main{ext}", "w", encoding="utf-8") as f:
            f.write(code)

    student_dirs = [d for d in task_dir.iterdir() if d.is_dir()]
    if len(student_dirs) < 2:
        return {"error": "需要至少2份提交"}

    result_dir = JPLAG_RESULTS_DIR / task_id
    result_dir.mkdir(parents=True, exist_ok=True)
    for item in result_dir.iterdir():
        if item.is_dir():
            shutil.rmtree(item)
        else:
            item.unlink()

    cmd = ["java", "-jar", str(Path(JPLAG_JAR_PATH).resolve()),
           "-l", LANGUAGE_MAP.get(language, "cpp"),
           "-r", str(result_dir), "-t", "4", str(task_dir)]

    try:
        subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        return _parse_jplag_results(task_id, result_dir)
    except Exception as e:
        return {"error": f"JPlag 运行失败: {e}"}


def _parse_jplag_results(task_id: str, result_dir: Path) -> Dict[str, Any]:
    """解析JPlag结果."""
    import zipfile
    overview_file = result_dir / "overview.json"
    if not overview_file.exists():
        zip_file = result_dir / "results.zip"
        if zip_file.exists():
            with zipfile.ZipFile(zip_file, 'r') as z:
                z.extractall(result_dir)

    if not overview_file.exists():
        return {"error": "未找到查重结果文件"}

    with open(overview_file, "r", encoding="utf-8") as f:
        overview = json.load(f)

    comparisons = []
    max_similarity = {}

    for comp in overview.get("comparisons", []):
        sid_a = comp.get("firstSubmissionId", "")
        sid_b = comp.get("secondSubmissionId", "")
        sim = comp.get("similarity", 0) * 100
        comparisons.append({
            "student_a": sid_a, "student_b": sid_b,
            "similarity": round(sim, 1),
            "matched_lines": len(comp.get("matches", []))
        })
        for sid, other in [(sid_a, sid_b), (sid_b, sid_a)]:
            if sid not in max_similarity or sim > max_similarity[sid]["value"]:
                max_similarity[sid] = {"value": round(sim, 1), "with": other}

    for sid, data in max_similarity.items():
        try:
            update_plagiarism(sid, task_id, data["value"], data["with"])
        except Exception:
            pass

    return {
        "task_id": task_id,
        "total_submissions": len(overview.get("submissionFolderPath", [])),
        "comparisons": comparisons,
        "max_similarity": max_similarity,
        "engine": "jplag"
    }
