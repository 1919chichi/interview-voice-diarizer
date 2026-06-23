from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

from errors import ConfigError


@dataclass(frozen=True)
class VolcAsrConfig:
    api_key: str
    resource_id: str
    flash_resource_id: str
    submit_url: str = "https://openspeech.bytedance.com/api/v3/auc/bigmodel/submit"
    query_url: str = "https://openspeech.bytedance.com/api/v3/auc/bigmodel/query"
    flash_url: str = "https://openspeech.bytedance.com/api/v3/auc/bigmodel/recognize/flash"


@dataclass(frozen=True)
class VolcArkConfig:
    api_key: str
    model: str
    base_url: str = "https://ark.cn-beijing.volces.com/api/v3"
    timeout_seconds: float = 600.0
    max_tokens: int = 16000


def load_environment() -> None:
    """从 .env 文件加载环境变量。"""
    load_dotenv()


def require_env(name: str) -> str:
    """读取必要环境变量，缺失或为空时抛出 ConfigError。"""
    value = os.getenv(name)
    if not value:
        raise ConfigError(f"缺少环境变量 {name}。请复制 .env.example 为 .env 并填写。")
    return value


def optional_float_env(name: str, default: float) -> float:
    """读取可选浮点环境变量，缺失时返回默认值，格式非法或非正数时抛出 ConfigError。"""
    value = os.getenv(name)
    if value is None:
        return default
    try:
        parsed = float(value)
    except ValueError as exc:
        raise ConfigError(f"环境变量 {name} 必须是数字。") from exc
    if parsed <= 0:
        raise ConfigError(f"环境变量 {name} 必须大于 0。")
    return parsed


def optional_int_env(name: str, default: int) -> int:
    """读取可选整数环境变量，缺失时返回默认值，格式非法或非正数时抛出 ConfigError。"""
    value = os.getenv(name)
    if value is None:
        return default
    try:
        parsed = int(value)
    except ValueError as exc:
        raise ConfigError(f"环境变量 {name} 必须是整数。") from exc
    if parsed <= 0:
        raise ConfigError(f"环境变量 {name} 必须大于 0。")
    return parsed


def load_asr_config() -> VolcAsrConfig:
    """从环境变量构建火山 ASR 配置。"""
    return VolcAsrConfig(
        api_key=require_env("VOLC_ASR_API_KEY"),
        resource_id=os.getenv("VOLC_ASR_RESOURCE_ID", "volc.seedasr.auc"),
        flash_resource_id=os.getenv("VOLC_ASR_FLASH_RESOURCE_ID", "volc.bigasr.auc_turbo"),
    )


def load_ark_config() -> VolcArkConfig:
    """从环境变量构建火山方舟 LLM 配置。"""
    return VolcArkConfig(
        api_key=require_env("VOLC_ARK_API_KEY"),
        model=require_env("VOLC_ARK_MODEL"),
        base_url=os.getenv("VOLC_ARK_BASE_URL", "https://ark.cn-beijing.volces.com/api/v3"),
        timeout_seconds=optional_float_env("VOLC_ARK_TIMEOUT_SECONDS", 600.0),
        max_tokens=optional_int_env("VOLC_ARK_MAX_TOKENS", 16000),
    )
