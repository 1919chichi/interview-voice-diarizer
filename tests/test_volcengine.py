import httpx
import pytest

from config import VolcArkConfig, load_ark_config
from errors import ApiError
from providers.volcengine import VolcArkClient


def test_ark_client_wraps_read_timeout_as_api_error(monkeypatch) -> None:
    def raise_timeout(*args, **kwargs):
        raise httpx.ReadTimeout("read timed out")

    monkeypatch.setattr("providers.volcengine.httpx.post", raise_timeout)
    client = VolcArkClient(VolcArkConfig(api_key="key", model="model"))

    with pytest.raises(ApiError, match="方舟分析超时"):
        client.chat_json([{"role": "user", "content": "hello"}])


def test_load_ark_config_reads_timeout_and_max_tokens(monkeypatch) -> None:
    """方舟配置应从环境变量读取长录音所需的超时和输出 token 上限。"""
    monkeypatch.setenv("VOLC_ARK_API_KEY", "key")
    monkeypatch.setenv("VOLC_ARK_MODEL", "model")
    monkeypatch.setenv("VOLC_ARK_TIMEOUT_SECONDS", "600")
    monkeypatch.setenv("VOLC_ARK_MAX_TOKENS", "16000")

    config = load_ark_config()

    assert config.timeout_seconds == 600.0
    assert config.max_tokens == 16000


def test_ark_client_uses_configured_timeout_and_max_tokens(monkeypatch) -> None:
    """方舟请求应使用配置中的超时和 max_tokens，避免长复盘被默认边界截断。"""
    calls: list[dict] = []

    def fake_post(*args, **kwargs):
        """记录方舟 HTTP 请求参数并返回最小合法 JSON 响应。"""
        calls.append(kwargs)
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": '{"ok": true}'}}]},
        )

    monkeypatch.setattr("providers.volcengine.httpx.post", fake_post)
    client = VolcArkClient(
        VolcArkConfig(
            api_key="key",
            model="model",
            timeout_seconds=600.0,
            max_tokens=16000,
        )
    )

    assert client.chat_json([{"role": "user", "content": "hello"}]) == {"ok": True}
    assert calls[0]["timeout"] == 600.0
    assert calls[0]["json"]["max_tokens"] == 16000
