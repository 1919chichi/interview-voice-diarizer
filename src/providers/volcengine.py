from __future__ import annotations

import base64
import json
import time
import uuid
from pathlib import Path
from typing import Any

import httpx

from config import VolcArkConfig, VolcAsrConfig
from errors import ApiError

SUCCESS_CODE = "20000000"
PENDING_CODES = {"20000001", "20000002"}


class VolcAsrClient:
    def __init__(self, config: VolcAsrConfig, timeout: float = 120.0) -> None:
        """初始化火山 ASR 客户端，保存配置和 HTTP 超时时间。"""
        self.config = config
        self.timeout = timeout

    def recognize_flash(self, audio_path: Path, audio_format: str) -> dict[str, Any]:
        """以 base64 内嵌文件方式调用极速版 ASR，同步返回识别结果。"""
        task_id = str(uuid.uuid4())
        headers = self._headers(task_id, self.config.flash_resource_id)
        body = self._request_body(audio_path=audio_path, audio_format=audio_format)
        response = httpx.post(
            self.config.flash_url,
            json=body,
            headers=headers,
            timeout=self.timeout,
        )
        return self._parse_asr_response(response, "极速识别")

    def submit_url_and_poll(
        self,
        audio_url: str,
        audio_format: str,
        poll_interval: float = 5.0,
        max_wait_seconds: float = 1800.0,
    ) -> dict[str, Any]:
        """提交公网 URL 的标准版识别任务，轮询直至成功或超时。"""
        task_id = str(uuid.uuid4())
        headers = self._headers(task_id, self.config.resource_id)
        body = self._request_body(audio_url=audio_url, audio_format=audio_format)
        submit_response = httpx.post(
            self.config.submit_url,
            json=body,
            headers=headers,
            timeout=self.timeout,
        )
        self._ensure_status(submit_response, "提交识别任务")

        deadline = time.monotonic() + max_wait_seconds
        while time.monotonic() < deadline:
            query_response = httpx.post(
                self.config.query_url,
                json={},
                headers=headers,
                timeout=self.timeout,
            )
            status = query_response.headers.get("X-Api-Status-Code", "")
            if status == SUCCESS_CODE:
                return self._parse_asr_response(query_response, "查询识别结果")
            if status not in PENDING_CODES:
                self._ensure_status(query_response, "查询识别结果")
            time.sleep(poll_interval)
        raise ApiError(f"识别任务超时：等待超过 {int(max_wait_seconds)} 秒。")

    def _headers(self, request_id: str, resource_id: str) -> dict[str, str]:
        """构建火山 ASR HTTP 请求头，包含认证 key、资源 ID 和请求 ID。"""
        return {
            "Content-Type": "application/json",
            "X-Api-Key": self.config.api_key,
            "X-Api-Resource-Id": resource_id,
            "X-Api-Request-Id": request_id,
            "X-Api-Sequence": "-1",
        }

    def _request_body(
        self,
        audio_format: str,
        audio_path: Path | None = None,
        audio_url: str | None = None,
    ) -> dict[str, Any]:
        """构建 ASR 请求体，audio_path 时内嵌 base64 数据，audio_url 时使用公网地址。"""
        audio: dict[str, Any] = {
            "format": audio_format,
            "language": "zh-CN",
        }
        if audio_path:
            audio["data"] = base64.b64encode(audio_path.read_bytes()).decode("utf-8")
        if audio_url:
            audio["url"] = audio_url
        return {
            "user": {"uid": "interview-voice-diarizer"},
            "audio": audio,
            "request": {
                "model_name": "bigmodel",
                "enable_itn": True,
                "enable_punc": True,
                "enable_ddc": True,
                "show_utterances": True,
                "enable_speaker_info": True,
            },
        }

    def _parse_asr_response(self, response: httpx.Response, action: str) -> dict[str, Any]:
        """校验 ASR 响应状态并解析响应体为 JSON，响应为空时返回空字典。"""
        self._ensure_status(response, action)
        if not response.content:
            return {}
        try:
            return response.json()
        except json.JSONDecodeError as exc:
            raise ApiError(f"{action} 返回不是合法 JSON：{response.text[:300]}") from exc

    def _ensure_status(self, response: httpx.Response, action: str) -> None:
        """检查 ASR 响应的 X-Api-Status-Code 和 HTTP 状态码，异常时抛出 ApiError。"""
        status = response.headers.get("X-Api-Status-Code")
        message = response.headers.get("X-Api-Message", "")
        if status and status != SUCCESS_CODE:
            raise ApiError(f"{action}失败：{status} {message}")
        if response.status_code >= 400:
            raise ApiError(f"{action}失败：HTTP {response.status_code} {response.text[:300]}")


class VolcArkClient:
    def __init__(self, config: VolcArkConfig, timeout: float | None = None) -> None:
        """初始化火山方舟 LLM 客户端，保存配置和 HTTP 超时时间。"""
        self.config = config
        self.timeout = config.timeout_seconds if timeout is None else timeout

    def chat_json(self, messages: list[dict[str, str]]) -> dict[str, Any]:
        """发送 chat completion 请求，以 json_object 格式强制输出，返回解析后的 JSON 内容。"""
        url = f"{self.config.base_url.rstrip('/')}/chat/completions"
        payload = {
            "model": self.config.model,
            "messages": messages,
            "temperature": 0.2,
            "response_format": {"type": "json_object"},
            "max_tokens": self.config.max_tokens,
        }
        try:
            response = httpx.post(
                url,
                json=payload,
                headers={
                    "Authorization": f"Bearer {self.config.api_key}",
                    "Content-Type": "application/json",
                },
                timeout=self.timeout,
            )
        except httpx.TimeoutException as exc:
            raise ApiError(f"方舟分析超时：等待超过 {int(self.timeout)} 秒。") from exc
        if response.status_code >= 400:
            raise ApiError(f"方舟分析失败：HTTP {response.status_code} {response.text[:300]}")
        data = response.json()
        content = data["choices"][0]["message"]["content"]
        try:
            return json.loads(content)
        except json.JSONDecodeError as exc:
            raise ApiError(f"方舟返回的内容不是 JSON：{content[:300]}") from exc
