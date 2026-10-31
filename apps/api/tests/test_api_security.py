"""API exposure rules. The Gemini dependency is faked, so nothing here spends quota."""

import pytest
from fastapi.testclient import TestClient

from app.api.v1.ai import ContentIdea, ContentIdeas
from app.config import get_settings
from app.main import create_app
from app.services.gemini import (
    GeminiInvalidResponseError,
    GeminiRequestError,
    GeminiUnavailableError,
    get_gemini,
)

KEY = "unit-test-internal-key"
UPSTREAM_DETAIL = "project 123456789012 is not enabled"


class FakeGemini:
    model = "fake-model"

    def __init__(self, failure=None):
        self.failure = failure
        self.calls = 0

    async def generate_json(self, prompt, schema, *, system=None):
        self.calls += 1
        if self.failure:
            raise self.failure
        idea = ContentIdea(title="Squats", description="A long enough description", format="reel")
        return ContentIdeas(ideas=[idea, idea, idea])


@pytest.fixture
def settings_env(monkeypatch):
    monkeypatch.setenv("INTERNAL_API_KEY", KEY)
    monkeypatch.setenv("APP_ENV", "development")
    get_settings.cache_clear()
    yield monkeypatch
    get_settings.cache_clear()


def client_with(gemini):
    app = create_app()
    app.dependency_overrides[get_gemini] = lambda: gemini
    return TestClient(app)


@pytest.mark.parametrize(
    "headers", [{}, {"X-Internal-Key": "wrong"}, {"X-Internal-Key": ""}], ids=["none", "wrong", "empty"]
)
def test_ai_endpoint_refuses_without_valid_key_and_spends_nothing(settings_env, headers):
    gemini = FakeGemini()
    r = client_with(gemini).post("/api/v1/ai/test", headers=headers)
    assert r.status_code == 403
    assert gemini.calls == 0


def test_ai_endpoint_refuses_everyone_when_no_key_is_configured(settings_env):
    settings_env.setenv("INTERNAL_API_KEY", "")
    get_settings.cache_clear()
    gemini = FakeGemini()
    r = client_with(gemini).post("/api/v1/ai/test", headers={"X-Internal-Key": ""})
    assert r.status_code == 403
    assert gemini.calls == 0


def test_ai_endpoint_works_with_valid_key(settings_env):
    r = client_with(FakeGemini()).post("/api/v1/ai/test", headers={"X-Internal-Key": KEY})
    assert r.status_code == 200
    assert len(r.json()["result"]["ideas"]) == 3


@pytest.mark.parametrize(
    "failure,status",
    [
        (GeminiRequestError(UPSTREAM_DETAIL), 502),
        (GeminiInvalidResponseError(UPSTREAM_DETAIL), 502),
        (GeminiUnavailableError(UPSTREAM_DETAIL), 503),
    ],
)
def test_ai_errors_never_expose_upstream_text(settings_env, failure, status):
    r = client_with(FakeGemini(failure)).post("/api/v1/ai/test", headers={"X-Internal-Key": KEY})
    assert r.status_code == status
    assert "123456789012" not in r.text


@pytest.mark.parametrize("env,expected", [("development", 200), ("staging", 404), ("production", 404)])
@pytest.mark.parametrize("path", ["/docs", "/redoc", "/openapi.json"])
def test_api_docs_only_public_in_development(settings_env, env, expected, path):
    settings_env.setenv("APP_ENV", env)
    get_settings.cache_clear()
    assert TestClient(create_app()).get(path).status_code == expected
