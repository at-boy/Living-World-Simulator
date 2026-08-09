import pytest

from living_world.perception.local_llm_http import (
    LocalLLMHttpError,
    validate_local_base_url,
)


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("http://127.0.0.1:11434/", "http://127.0.0.1:11434"),
        ("http://localhost:8080", "http://localhost:8080"),
        ("http://[::1]:8080/", "http://[::1]:8080"),
    ],
)
def test_validate_local_base_url_accepts_loopback_urls(
    url: str,
    expected: str,
) -> None:
    assert validate_local_base_url(url) == expected


@pytest.mark.parametrize(
    "url",
    [
        "https://ollama.com",
        "http://192.168.1.10:11434",
        "http://example.com",
        "not-a-url",
    ],
)
def test_validate_local_base_url_rejects_non_local_urls(url: str) -> None:
    with pytest.raises(ValueError, match="loopback HTTP URL"):
        validate_local_base_url(url)


def test_http_error_message_does_not_include_response_body() -> None:
    error = LocalLLMHttpError("Local LLM server returned HTTP 500.")

    assert str(error) == "Local LLM server returned HTTP 500."
