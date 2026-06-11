from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

from interview_voice_diarizer.errors import ConfigError


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


def load_environment() -> None:
    load_dotenv()


def require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise ConfigError(f"缺少环境变量 {name}。请复制 .env.example 为 .env 并填写。")
    return value


def load_asr_config() -> VolcAsrConfig:
    return VolcAsrConfig(
        api_key=require_env("VOLC_ASR_API_KEY"),
        resource_id=os.getenv("VOLC_ASR_RESOURCE_ID", "volc.seedasr.auc"),
        flash_resource_id=os.getenv("VOLC_ASR_FLASH_RESOURCE_ID", "volc.bigasr.auc_turbo"),
    )


def load_ark_config() -> VolcArkConfig:
    return VolcArkConfig(
        api_key=require_env("VOLC_ARK_API_KEY"),
        model=require_env("VOLC_ARK_MODEL"),
        base_url=os.getenv("VOLC_ARK_BASE_URL", "https://ark.cn-beijing.volces.com/api/v3"),
    )
