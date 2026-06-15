"""代码运行引擎.

编译并运行用户代码，返回编译错误、运行时输出等信息.
支持 C/C++、Python、Java.
"""

import subprocess
import tempfile
import os
import shutil
import signal
from pathlib import Path
from typing import Dict, Any, Optional

from app.utils.logger import get_logger

logger = get_logger(__name__)

# 运行超时（秒）
TIMEOUT = 10
# 输出最大字符数
MAX_OUTPUT = 5000


def _clean_temp_paths(text: str) -> str:
    """清理输出中的临时文件路径."""
    import re
    text = re.sub(r'[A-Z]:\\\\([^\\]+\\)*Temp\\code_run_[^\\]+\\', '', text)
    text = re.sub(r'[A-Z]:\\Users\\[^\\]+\\AppData\\Local\\Temp\\', '', text)
    text = re.sub(r'/tmp/code_run_[^/]+/', '', text)
    return text


def run_code(code: str, language: str, stdin: str = "") -> Dict[str, Any]:
    """编译并运行代码.

    Args:
        code: 源代码
        language: 编程语言 (cpp/c/python/java)
        stdin: 标准输入

    Returns:
        {
            "success": bool,
            "stdout": str,
            "stderr": str,
            "exit_code": int,
            "timed_out": bool
        }
    """
    workdir = Path(tempfile.mkdtemp(prefix="code_run_"))

    try:
        if language in ("cpp", "c"):
            return _run_cpp(workdir, code, stdin)
        elif language == "python" or language == "python3":
            return _run_python(workdir, code, stdin)
        elif language == "java":
            return _run_java(workdir, code, stdin)
        else:
            return {
                "success": False,
                "stdout": "",
                "stderr": f"不支持的语言: {language}",
                "exit_code": -1,
                "timed_out": False
            }
    except Exception as e:
        logger.error(f"代码运行异常: {str(e)}", exc_info=True)
        return {
            "success": False,
            "stdout": "",
            "stderr": f"运行异常: {str(e)}",
            "exit_code": -1,
            "timed_out": False
        }
    finally:
        # 清理临时文件
        try:
            shutil.rmtree(workdir, ignore_errors=True)
        except Exception:
            pass


def _run_cpp(workdir: Path, code: str, stdin: str) -> Dict[str, Any]:
    """编译并运行 C/C++ 代码."""
    source_file = workdir / "main.cpp"
    output_file = workdir / "main.exe"

    with open(source_file, "w", encoding="utf-8") as f:
        f.write(code)

    # 编译
    gpp_cmd = ["g++", "-std=c++17", "-Wall", "-Wextra", "-o", str(output_file), str(source_file)]
    try:
        compile_result = subprocess.run(
            gpp_cmd,
            capture_output=True,
            text=True,
            timeout=30,
            cwd=str(workdir)
        )
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "stdout": "",
            "stderr": "❌ 编译超时（超过30秒）",
            "exit_code": -1,
            "timed_out": True
        }

    if compile_result.returncode != 0:
        # 编译错误
        stderr = compile_result.stderr or compile_result.stdout
        # 美化输出
        stderr = _format_compiler_error(stderr, "C++")
        return {
            "success": False,
            "stdout": "",
            "stderr": stderr,
            "exit_code": compile_result.returncode,
            "timed_out": False
        }

    # 运行
    return _run_executable(str(output_file), stdin)


def _run_python(workdir: Path, code: str, stdin: str) -> Dict[str, Any]:
    """运行 Python 代码."""
    source_file = workdir / "main.py"
    with open(source_file, "w", encoding="utf-8") as f:
        f.write(code)

    try:
        result = subprocess.run(
            ["python", str(source_file)],
            input=stdin,
            capture_output=True,
            text=True,
            timeout=TIMEOUT,
            cwd=str(workdir)
        )
        stdout = _clean_temp_paths(result.stdout[:MAX_OUTPUT]) if result.stdout else ""
        stderr = _clean_temp_paths(result.stderr[:MAX_OUTPUT]) if result.stderr else ""
        return {
            "success": result.returncode == 0,
            "stdout": stdout,
            "stderr": stderr,
            "exit_code": result.returncode,
            "timed_out": False
        }
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "stdout": "",
            "stderr": "❌ 运行超时（超过10秒）",
            "exit_code": -1,
            "timed_out": True
        }


def _run_java(workdir: Path, code: str, stdin: str) -> Dict[str, Any]:
    """编译并运行 Java 代码."""
    # 提取类名
    class_name = _extract_java_class(code) or "Main"
    source_file = workdir / f"{class_name}.java"

    with open(source_file, "w", encoding="utf-8") as f:
        f.write(code)

    # 编译
    try:
        compile_result = subprocess.run(
            ["javac", str(source_file)],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=str(workdir)
        )
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "stdout": "",
            "stderr": "❌ 编译超时（超过30秒）",
            "exit_code": -1,
            "timed_out": True
        }

    if compile_result.returncode != 0:
        stderr = _format_compiler_error(compile_result.stderr or compile_result.stdout, "Java")
        return {
            "success": False,
            "stdout": "",
            "stderr": stderr,
            "exit_code": compile_result.returncode,
            "timed_out": False
        }

    # 运行
    try:
        result = subprocess.run(
            ["java", class_name],
            input=stdin,
            capture_output=True,
            text=True,
            timeout=TIMEOUT,
            cwd=str(workdir)
        )
        stdout = _clean_temp_paths(result.stdout[:MAX_OUTPUT]) if result.stdout else ""
        stderr = _clean_temp_paths(result.stderr[:MAX_OUTPUT]) if result.stderr else ""
        return {
            "success": result.returncode == 0,
            "stdout": stdout,
            "stderr": stderr,
            "exit_code": result.returncode,
            "timed_out": False
        }
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "stdout": "",
            "stderr": "❌ 运行超时（超过10秒）",
            "exit_code": -1,
            "timed_out": True
        }


def _run_executable(exe_path: str, stdin: str) -> Dict[str, Any]:
    """运行编译后的可执行文件."""
    try:
        result = subprocess.run(
            [exe_path],
            input=stdin,
            capture_output=True,
            text=True,
            timeout=TIMEOUT,
        )
        stdout = _clean_temp_paths(result.stdout[:MAX_OUTPUT]) if result.stdout else ""
        stderr = _clean_temp_paths(result.stderr[:MAX_OUTPUT]) if result.stderr else ""
        return {
            "success": result.returncode == 0,
            "stdout": stdout,
            "stderr": stderr,
            "exit_code": result.returncode,
            "timed_out": False
        }
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "stdout": "",
            "stderr": "❌ 运行超时（超过10秒）",
            "exit_code": -1,
            "timed_out": True
        }


def _format_compiler_error(stderr: str, lang: str) -> str:
    """格式化编译器错误信息，更直观."""
    if not stderr:
        return f"❌ {lang} 编译失败（无详细错误信息）"

    # 简化路径显示，移除临时目录
    import re
    lines = stderr.split("\n")
    formatted = []
    for line in lines:
        # 移除临时目录路径前缀，只保留 main.cpp:line:col 格式
        cleaned = re.sub(r'^[A-Z]:(\\[^\\]+)+\\', '', line.strip())
        cleaned = re.sub(r'^/tmp/[^:]+:', '', cleaned)
        cleaned = re.sub(r'^[A-Z]:\\[^:]+\\', '', cleaned)

        if "error:" in cleaned:
            formatted.append(f"❌ {cleaned}")
        elif "warning:" in cleaned:
            formatted.append(f"⚠️ {cleaned}")
        elif cleaned:
            # 保留行号指示行（如 main.cpp:2:34）
            if re.match(r'main\.\w+:', cleaned) or '^' in cleaned:
                formatted.append(cleaned)
            elif re.match(r'\s+[~^]+\s*', cleaned):
                formatted.append(cleaned)

    if not formatted:
        # fallback: just clean paths
        result = re.sub(r'[A-Z]:(\\[^\\]+)+\\', '', stderr)
        return result[:MAX_OUTPUT]

    result = "\n".join(formatted[-15:])
    return result[:MAX_OUTPUT]


def _extract_java_class(code: str) -> Optional[str]:
    """从Java代码中提取public class名称."""
    import re
    match = re.search(r'public\s+class\s+(\w+)', code)
    if match:
        return match.group(1)
    match = re.search(r'class\s+(\w+)', code)
    if match:
        return match.group(1)
    return None
