"""fal.ai adapter for FLUX image and video generation, using the documented queue API."""

import logging
import time
from dataclasses import dataclass
from functools import lru_cache
from urllib.parse import urlsplit

import httpx

from app.core.config import get_settings

log = logging.getLogger(__name__)

QUEUE_URL = "https://queue.fal.run"
MAX_DOWNLOAD_BYTES = 200 * 1024 * 1024


class FalError(Exception):
    """Generation failed. Messages never contain the API key."""


@dataclass(frozen=True)
class GeneratedMedia:
    data: bytes
    content_type: str
    request_id: str
    seed: int | None


class FalClient:
    def __init__(self, api_key: str, *, timeout: float = 600, poll_seconds: float = 3):
        self._headers = {"Authorization": f"Key {api_key}", "Content-Type": "application/json"}
        self._timeout = timeout
        self._poll_seconds = poll_seconds
        self._http = httpx.Client(timeout=60)

    def _request(self, method: str, url: str, **kwargs) -> dict:
        try:
            response = self._http.request(method, url, headers=self._headers, **kwargs)
        except httpx.HTTPError as exc:
            raise FalError(f"fal request failed: {type(exc).__name__}") from exc
        if response.status_code >= 400:
            try:
                detail = response.json().get("detail", "")
            except ValueError:
                detail = ""
            raise FalError(f"fal returned {response.status_code}: {str(detail)[:200]}")
        return response.json()

    def _run(self, model: str, arguments: dict) -> tuple[str, dict]:
        submitted = self._request("POST", f"{QUEUE_URL}/{model}", json=arguments)
        request_id = submitted["request_id"]
        deadline = time.monotonic() + self._timeout
        while True:
            status = self._request("GET", submitted["status_url"])
            if status.get("error"):
                raise FalError(f"fal generation failed: {str(status['error'])[:200]}")
            if status.get("status") == "COMPLETED":
                return request_id, self._request("GET", submitted["response_url"])
            if time.monotonic() > deadline:
                raise FalError("fal generation timed out")
            time.sleep(self._poll_seconds)

    def _download(self, url: str) -> bytes:
        parts = urlsplit(url)
        host = parts.hostname or ""
        if parts.scheme != "https" or not (host == "fal.media" or host.endswith(".fal.media")):
            raise FalError("fal returned an unexpected file address")
        try:
            with self._http.stream("GET", url, timeout=300) as response:
                response.raise_for_status()
                chunks, size = [], 0
                for chunk in response.iter_bytes():
                    size += len(chunk)
                    if size > MAX_DOWNLOAD_BYTES:
                        raise FalError("fal returned a file that is too large")
                    chunks.append(chunk)
        except httpx.HTTPError as exc:
            raise FalError(f"fal download failed: {type(exc).__name__}") from exc
        return b"".join(chunks)

    def generate_image(self, model: str, prompt: str, *, image_size: str = "portrait_16_9") -> GeneratedMedia:
        request_id, result = self._run(
            model,
            {"prompt": prompt, "image_size": image_size, "num_images": 1, "output_format": "jpeg"},
        )
        if any(result.get("has_nsfw_concepts") or []):
            raise FalError("the image was blocked by the safety checker")
        image = result["images"][0]
        return GeneratedMedia(
            data=self._download(image["url"]),
            content_type=image.get("content_type") or "image/jpeg",
            request_id=request_id,
            seed=result.get("seed"),
        )

    def generate_video(
        self, model: str, prompt: str, *, duration: int = 5, aspect_ratio: str = "9:16"
    ) -> GeneratedMedia:
        request_id, result = self._run(
            model,
            {
                "prompt": prompt,
                "duration": str(duration),
                "resolution": "720p",
                "aspect_ratio": aspect_ratio,
                "generate_audio": False,
            },
        )
        video = result["video"]
        return GeneratedMedia(
            data=self._download(video["url"]),
            content_type=video.get("content_type") or "video/mp4",
            request_id=request_id,
            seed=result.get("seed"),
        )


@lru_cache
def get_fal() -> FalClient | None:
    settings = get_settings()
    return FalClient(settings.fal_key.get_secret_value()) if settings.fal_key else None
