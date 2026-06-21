import httpx
import pytest

from config import VolcArkConfig
from errors import ApiError
from providers.volcengine import VolcArkClient


def test_ark_client_wraps_read_timeout_as_api_error(monkeypatch) -> None:
    def raise_timeout(*args, **kwargs):
        raise httpx.ReadTimeout("read timed out")

    monkeypatch.setattr("providers.volcengine.httpx.post", raise_timeout)
    client = VolcArkClient(VolcArkConfig(api_key="key", model="model"))

    with pytest.raises(ApiError, match="方舟分析超时"):
        client.chat_json([{"role": "user", "content": "hello"}])
