"""Lets synchronous routes and graph nodes use the async Gemini service on one shared event loop."""

import asyncio
import threading
from functools import lru_cache
from typing import TypeVar

from pydantic import BaseModel

from app.core.config import get_settings
from app.integrations.gemini.service import GeminiService

T = TypeVar("T", bound=BaseModel)


class GeminiGateway:
    def __init__(self, service: GeminiService):
        self._service = service
        self._loop = asyncio.new_event_loop()
        threading.Thread(target=self._loop.run_forever, name="gemini-loop", daemon=True).start()

    @property
    def model(self) -> str:
        return self._service.model

    def generate_json(self, prompt: str, schema: type[T], *, system: str | None = None) -> T:
        coroutine = self._service.generate_json(prompt, schema, system=system)
        return asyncio.run_coroutine_threadsafe(coroutine, self._loop).result()


@lru_cache
def get_gateway() -> GeminiGateway:
    return GeminiGateway(GeminiService(get_settings()))
