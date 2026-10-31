"""Gemini service behaviour, using a fake client. No network calls or spend."""

import asyncio
from types import SimpleNamespace

import httpx
import pytest
from google.genai import errors
from pydantic import BaseModel

from app.config import Settings
from app.services.gemini import (
    GeminiInvalidResponseError,
    GeminiRequestError,
    GeminiService,
    GeminiUnavailableError,
)

SECRET = "test-key-must-never-appear"


class Idea(BaseModel):
    title: str


class FakeModels:
    def __init__(self, outcomes):
        self.outcomes = list(outcomes)
        self.calls = 0
        self.active = 0
        self.max_active = 0

    async def generate_content(self, **kwargs):
        self.calls += 1
        self.active += 1
        self.max_active = max(self.max_active, self.active)
        await asyncio.sleep(0)
        self.active -= 1
        outcome = self.outcomes.pop(0) if len(self.outcomes) > 1 else self.outcomes[0]
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


def service(outcomes, **overrides) -> tuple[GeminiService, FakeModels]:
    settings = Settings(
        _env_file=None,
        database_url="postgresql+psycopg://unused",
        gemini_api_key=SECRET,
        gemini_model="test-model",
        **overrides,
    )
    svc = GeminiService(settings)
    models = FakeModels(outcomes)
    svc._client = SimpleNamespace(aio=SimpleNamespace(models=models))
    return svc, models


def api_error(cls, code: int):
    return cls(code, {"error": {"code": code, "message": f"upstream detail {code}"}})


def ok(text: str, parsed=None):
    return SimpleNamespace(text=text, parsed=parsed)


@pytest.fixture(autouse=True)
def no_backoff_delay(monkeypatch):
    real_sleep = asyncio.sleep

    async def instant(_delay):
        await real_sleep(0)

    monkeypatch.setattr("app.services.gemini.asyncio.sleep", instant)


def test_generate_text_returns_text():
    svc, _ = service([ok("hello")])
    assert asyncio.run(svc.generate_text("hi")) == "hello"


def test_empty_text_is_rejected():
    svc, _ = service([ok("")])
    with pytest.raises(GeminiInvalidResponseError):
        asyncio.run(svc.generate_text("hi"))


def test_generate_json_validates_text_when_sdk_has_no_parsed_value():
    svc, _ = service([ok('{"title": "Squats"}')])
    assert asyncio.run(svc.generate_json("hi", Idea)).title == "Squats"


@pytest.mark.parametrize("text", ["not json", '{"wrong": 1}', ""])
def test_generate_json_rejects_invalid_output(text):
    svc, _ = service([ok(text)])
    with pytest.raises(GeminiInvalidResponseError):
        asyncio.run(svc.generate_json("hi", Idea))


@pytest.mark.parametrize(
    "failure",
    [
        api_error(errors.ServerError, 503),
        api_error(errors.ClientError, 429),
        httpx.ReadTimeout("slow"),
        TimeoutError(),
    ],
)
def test_transient_failures_are_retried(failure):
    svc, models = service([failure, ok("recovered")])
    assert asyncio.run(svc.generate_text("hi")) == "recovered"
    assert models.calls == 2


@pytest.mark.parametrize("code", [400, 401, 403, 404])
def test_permanent_failures_are_not_retried(code):
    svc, models = service([api_error(errors.ClientError, code)])
    with pytest.raises(GeminiRequestError):
        asyncio.run(svc.generate_text("hi"))
    assert models.calls == 1


def test_retries_are_bounded():
    svc, models = service([api_error(errors.ServerError, 503)], gemini_max_retries=2)
    with pytest.raises(GeminiUnavailableError):
        asyncio.run(svc.generate_text("hi"))
    assert models.calls == 3


def test_concurrency_is_capped():
    svc, models = service([ok("x")], gemini_max_concurrency=2)

    async def run():
        await asyncio.gather(*(svc.generate_text("hi") for _ in range(8)))

    asyncio.run(run())
    assert models.calls == 8 and models.max_active <= 2


def test_api_key_never_appears_in_errors_or_settings_repr():
    svc, _ = service([api_error(errors.ClientError, 403)])
    with pytest.raises(GeminiRequestError) as exc:
        asyncio.run(svc.generate_text("hi"))
    assert SECRET not in str(exc.value)
    settings = Settings(
        _env_file=None, database_url="postgresql+psycopg://unused", gemini_api_key=SECRET, gemini_model="m"
    )
    assert SECRET not in repr(settings)
