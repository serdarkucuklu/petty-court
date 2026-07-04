import pytest


def _server_error(code=503):
    from google.genai import errors
    return errors.ServerError(code, {"error": {"message": "high demand", "status": "UNAVAILABLE"}})


def _client_error(code=429):
    from google.genai import errors
    return errors.ClientError(code, {"error": {"message": "quota exceeded", "status": "RESOURCE_EXHAUSTED"}})


def test_retries_transient_then_succeeds():
    from src.gemini_retry import call_with_retry
    n = {"c": 0}

    def fn():
        n["c"] += 1
        if n["c"] < 3:
            raise _server_error()
        return "ok"

    assert call_with_retry(fn, tries=4, base_delay=0, sleep=lambda s: None) == "ok"
    assert n["c"] == 3


def test_reraises_after_exhaustion():
    from src.gemini_retry import call_with_retry
    from google.genai import errors

    def fn():
        raise _server_error()

    with pytest.raises(errors.ServerError):
        call_with_retry(fn, tries=2, base_delay=0, sleep=lambda s: None)


def test_does_not_retry_client_error():
    """429/quota (ClientError) must NOT be retried."""
    from src.gemini_retry import call_with_retry
    from google.genai import errors
    n = {"c": 0}

    def fn():
        n["c"] += 1
        raise _client_error()

    with pytest.raises(errors.ClientError):
        call_with_retry(fn, tries=4, base_delay=0, sleep=lambda s: None)
    assert n["c"] == 1
