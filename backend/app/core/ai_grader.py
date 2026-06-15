"""AI评分引擎模块.

调用DeepSeek API对学生代码进行智能评分.
"""

import aiohttp
import json
import asyncio
from typing import Dict, Any, Optional

from app.config import DEEPSEEK_API_KEY, DEEPSEEK_API_URL, DEEPSEEK_MODEL
from app.utils.logger import get_logger

logger = get_logger(__name__)

# 默认评分标准（可配置）
DEFAULT_RUBRIC = """
【评分标准】
1. 功能正确性（40分）：代码是否能正确实现题目要求的功能，包括边界条件处理
2. 代码规范（20分）：命名规范、注释、缩进、代码格式、是否符合语言规范
3. 算法效率（20分）：时间复杂度、空间复杂度是否合理，是否有优化空间
4. 代码结构（20分）：模块化、可读性、逻辑清晰度、异常处理

【输出要求】
请以JSON格式输出，不要包含任何其他文字：
{
    "total_score": 整数(0-100),
    "details": [
        {"category": "功能正确性", "score": 整数, "max_score": 40, "comment": "具体评语"},
        {"category": "代码规范", "score": 整数, "max_score": 20, "comment": "具体评语"},
        {"category": "算法效率", "score": 整数, "max_score": 20, "comment": "具体评语"},
        {"category": "代码结构", "score": 整数, "max_score": 20, "comment": "具体评语"}
    ],
    "problems": ["问题1", "问题2", ...],
    "suggestions": "具体的改进建议，包含代码示例"
}
"""


async def grade_code(
    code: str,
    language: str,
    task_desc: str = "",
    timeout: int = 30
) -> Dict[str, Any]:
    """对代码进行AI评分.

    Args:
        code: 学生代码
        language: 编程语言
        task_desc: 任务描述
        timeout: 请求超时时间（秒）

    Returns:
        评分结果字典
    """
    if not DEEPSEEK_API_KEY:
        logger.error("DeepSeek API Key 未配置")
        return _fallback_grade("API Key 未配置")

    prompt = _build_prompt(code, language, task_desc)

    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": DEEPSEEK_MODEL,
        "messages": [
            {
                "role": "system",
                "content": "你是一位资深的编程教学专家，擅长代码评审和评分。请严格按照评分标准进行评分，给出具体的改进建议。"
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        "temperature": 0.3,
        "max_tokens": 2000,
        "response_format": {"type": "json_object"}
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                DEEPSEEK_API_URL,
                headers=headers,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=timeout)
            ) as response:

                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"DeepSeek API 错误: status={response.status}, body={error_text}")
                    return _fallback_grade(f"API 返回错误: {response.status}")

                data = await response.json()
                content = data["choices"][0]["message"]["content"]

                result = _parse_response(content)
                logger.info(f"评分完成: total_score={result.get('total_score', 0)}")
                return result

    except asyncio.TimeoutError:
        logger.error("DeepSeek API 请求超时")
        return _fallback_grade("评分请求超时")
    except Exception as e:
        logger.error(f"评分异常: {str(e)}", exc_info=True)
        return _fallback_grade(f"评分异常: {str(e)}")


def _build_prompt(code: str, language: str, task_desc: str) -> str:
    """构建评分提示词."""
    if task_desc:
        task_section = (
            f"【题目要求】\n{task_desc}\n\n"
            f"【学生代码】\n```{language}\n{code}\n```"
        )
    else:
        task_section = f"【学生代码】\n```{language}\n{code}\n```"

    return f"""请对以下{language}代码进行评分。

{task_section}

{DEFAULT_RUBRIC}
"""


def _parse_response(content: str) -> Dict[str, Any]:
    """解析API响应内容."""
    # 清理可能的markdown代码块标记
    content = content.strip()
    if content.startswith("```json"):
        content = content[7:]
    if content.startswith("```"):
        content = content[3:]
    if content.endswith("```"):
        content = content[:-3]
    content = content.strip()

    try:
        result = json.loads(content)
        # 验证必要字段
        if "total_score" not in result:
            raise ValueError("缺少 total_score 字段")
        if "details" not in result or not isinstance(result["details"], list):
            raise ValueError("缺少 details 字段")

        # 确保分数在合理范围内
        result["total_score"] = max(0, min(100, int(result.get("total_score", 0))))

        return result

    except json.JSONDecodeError as e:
        logger.error(f"JSON解析失败: {content[:200]}...")
        return _fallback_grade("评分结果解析失败")
    except ValueError as e:
        logger.error(f"评分结果格式错误: {str(e)}")
        return _fallback_grade("评分结果格式错误")


def _fallback_grade(reason: str = "评分服务暂时不可用") -> Dict[str, Any]:
    """返回降级评分结果."""
    return {
        "total_score": 0,
        "details": [
            {
                "category": "功能正确性",
                "score": 0,
                "max_score": 40,
                "comment": reason
            },
            {
                "category": "代码规范",
                "score": 0,
                "max_score": 20,
                "comment": "-"
            },
            {
                "category": "算法效率",
                "score": 0,
                "max_score": 20,
                "comment": "-"
            },
            {
                "category": "代码结构",
                "score": 0,
                "max_score": 20,
                "comment": "-"
            }
        ],
        "problems": [reason],
        "suggestions": "请检查网络连接或联系管理员。如果问题持续，请稍后重试。"
    }
