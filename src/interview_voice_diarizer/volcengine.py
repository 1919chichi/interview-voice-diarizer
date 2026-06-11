from __future__ import annotations

import base64
import json
import time
import uuid
from pathlib import Path
from typing import Any

import httpx

from interview_voice_diarizer.config import VolcArkConfig, VolcAsrConfig
from interview_voice_diarizer.errors import ApiError

SUCCESS_CODE = "20000000"
PENDING_CODES = {"20000001", "20000002"}


class VolcAsrClient:
    def __init__(self, config: VolcAsrConfig, timeout: float = 120.0) -> None:
        self.config = config
        self.timeout = timeout

    def recognize_flash(self, audio_path: Path, audio_format: str) -> dict[str, Any]:
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
        self._ensure_status(response, action)
        if not response.content:
            return {}
        try:
            return response.json()
        except json.JSONDecodeError as exc:
            raise ApiError(f"{action} 返回不是合法 JSON：{response.text[:300]}") from exc

    def _ensure_status(self, response: httpx.Response, action: str) -> None:
        status = response.headers.get("X-Api-Status-Code")
        message = response.headers.get("X-Api-Message", "")
        if status and status != SUCCESS_CODE:
            raise ApiError(f"{action}失败：{status} {message}")
        if response.status_code >= 400:
            raise ApiError(f"{action}失败：HTTP {response.status_code} {response.text[:300]}")


class VolcArkClient:
    def __init__(self, config: VolcArkConfig, timeout: float = 120.0) -> None:
        self.config = config
        self.timeout = timeout

    def chat_json(self, messages: list[dict[str, str]]) -> dict[str, Any]:
        url = f"{self.config.base_url.rstrip('/')}/chat/completions"
        payload = {
            "model": self.config.model,
            "messages": messages,
            "temperature": 0.2,
            "response_format": {"type": "json_object"},
        }
        response = httpx.post(
            url,
            json=payload,
            headers={
                "Authorization": f"Bearer {self.config.api_key}",
                "Content-Type": "application/json",
            },
            timeout=self.timeout,
        )
        if response.status_code >= 400:
            raise ApiError(f"方舟分析失败：HTTP {response.status_code} {response.text[:300]}")
        data = response.json()
        content = data["choices"][0]["message"]["content"]
        try:
            return json.loads(content)
        except json.JSONDecodeError as exc:
            raise ApiError(f"方舟返回的内容不是 JSON：{content[:300]}") from exc
