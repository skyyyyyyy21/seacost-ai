"""
统一 LLM 客户端模块

支持 OpenAI 兼容格式（DeepSeek、OpenAI 等）
"""
import os
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# 全局客户端实例
_client = None
_model = None


def init_llm_client():
    """初始化 LLM 客户端"""
    global _client, _model
    
    # 默认 API Key（用于演示）
    default_key = "sk-83df2051487d4a1488793fbe13891de9"
    api_key = os.getenv("ANTHROPIC_API_KEY", "").strip() or default_key
    
    if not api_key:
        logger.warning("未配置 API Key，LLM 功能不可用")
        return False
    
    # 模型名称
    _model = os.getenv("ANTHROPIC_MODEL", "deepseek-chat")
    
    # API Base URL
    base_url = os.getenv("ANTHROPIC_BASE_URL", "").strip()
    if not base_url:
        base_url = "https://api.deepseek.com/v1"
    
    # 确保 base_url 以 /v1 结尾（OpenAI 格式）
    if not base_url.endswith("/v1"):
        base_url = base_url.rstrip("/") + "/v1"
    
    try:
        from openai import AsyncOpenAI
        _client = AsyncOpenAI(
            api_key=api_key,
            base_url=base_url
        )
        logger.info(f"LLM 客户端初始化成功: model={_model}, base_url={base_url}")
        return True
    except Exception as e:
        logger.error(f"LLM 客户端初始化失败: {e}")
        return False


async def chat_completion(
    messages: List[Dict[str, str]],
    temperature: float = 0.3,
    max_tokens: int = 1000,
    **kwargs
) -> str:
    """
    调用 LLM 进行对话补全
    
    Args:
        messages: 消息列表，格式为 [{"role": "user", "content": "..."}]
        temperature: 温度参数
        max_tokens: 最大 token 数
        **kwargs: 其他参数
    
    Returns:
        LLM 回复文本
    """
    global _client, _model
    
    if _client is None:
        raise RuntimeError("LLM 客户端未初始化")
    
    try:
        response = await _client.chat.completions.create(
            model=_model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs
        )
        return response.choices[0].message.content or ""
    except Exception as e:
        logger.error(f"LLM 调用失败: {type(e).__name__}: {e}")
        raise


def is_llm_available() -> bool:
    """检查 LLM 是否可用"""
    return _client is not None
