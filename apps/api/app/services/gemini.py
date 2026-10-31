import asyncio
import logging
import random
from functools import lru_cache
from typing import TypeVar

import httpx
from google import genai
from google.genai import errors, types
from pydantic import BaseModel, ValidationError

from app.config import Settings, get_settings

log = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

_RETRYABLE_STATUS = {408, 429, 500, 502, 503, 504}


class GeminiError(Exception):
    """Base class for Gemini service failures. Messages never contain the API key."""


class GeminiUnavailableError(GeminiError):
    """Upstream failed after retries (timeouts, rate limits, 5xx)."""


class GeminiRequestError(GeminiError):
    """Non-retryable upstream error (bad model, bad request, auth)."""


class GeminiInvalidResponseError(GeminiError):
    """Model output could not be parsed/validated against the requested schema."""


class GeminiService:
    def __init__(self, settings: Settings):
        self._model = settings.gemini_model
        self._timeout = settings.gemini_timeout_s
        self._max_retries = settings.gemini_max_retries
        self._sem = asyncio.Semaphore(settings.gemini_max_concurrency)
        # Per-request timeout is enforced by the SDK (ms) and by asyncio.wait_for.
        self._client = genai.Client(
            api_key=settings.gemini_api_key.get_secret_value(),
            http_options=types.HttpOptions(timeout=int(self._timeout * 1000)),
        )

    @property
    def model(self) -> str:
        return self._model

    async def generate_text(self, prompt: str, *, system: str | None = None) -> str:
        config = types.GenerateContentConfig(system_instruction=system)
        resp = await self._call(prompt, config)
        if not resp.text:
            raise GeminiInvalidResponseError("empty response from model")
        return resp.text

    async def generate_json(self, prompt: str, schema: type[T], *, system: str | None = None) -> T:
        """Structured output: the model is constrained to `schema`, then re-validated by Pydantic."""
        config = types.GenerateContentConfig(
            system_instruction=system,
            response_mime_type="application/json",
            response_schema=schema,
        )
        resp = await self._call(prompt, config)
        try:
            if isinstance(resp.parsed, schema):
                return resp.parsed
            return schema.model_validate_json(resp.text or "")
        except (ValidationError, ValueError) as exc:
            raise GeminiInvalidResponseError("model output failed schema validation") from exc

    async def _call(self, prompt: str, config: types.GenerateContentConfig):
        attempt = 0
        while True:
            attempt += 1
            try:
                async with self._sem:
                    return await asyncio.wait_for(
                        self._client.aio.models.generate_content(
                            model=self._model, contents=prompt, config=config
                        ),
                        timeout=self._timeout + 5,
                    )
            except (TimeoutError, httpx.TransportError, errors.APIError) as exc:
                retryable = isinstance(exc, (asyncio.TimeoutError, httpx.TransportError)) or (
                    getattr(exc, "code", None) in _RETRYABLE_STATUS
                )
                if not retryable:
                    raise GeminiRequestError(
                        f"gemini request rejected ({getattr(exc, 'code', 'unknown')}): "
                        f"{getattr(exc, 'message', None) or type(exc).__name__}"
                    ) from None
                if attempt > self._max_retries:
                    raise GeminiUnavailableError(f"gemini unavailable after {attempt} attempts") from None
                delay = min(8.0, 0.5 * 2 ** (attempt - 1)) + random.uniform(0, 0.25)  # noqa: S311
                log.warning(
                    "gemini attempt %d failed (%s); retrying in %.1fs", attempt, type(exc).__name__, delay
                )
                await asyncio.sleep(delay)


@lru_cache
def get_gemini() -> GeminiService:
    return GeminiService(get_settings())
