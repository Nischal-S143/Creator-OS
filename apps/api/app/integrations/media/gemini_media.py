"""Image and video generation through the same Gemini key used for text.

Verified live on 1 November 2026: both calls below returned real media on this key's project.
Image: models.generate_content(response_modalities=["IMAGE"]). Video: interactions.create(...),
which returns the clip inline as base64, or as a file URI to poll and download once it is large.
"""

import base64
import logging
import time
from dataclasses import dataclass
from functools import lru_cache

from google import genai
from google.genai import errors, types

from app.core.config import Settings, get_settings

log = logging.getLogger(__name__)

MAX_POLL_SECONDS = 180


class MediaGenerationError(Exception):
    """Generation failed. Messages never contain the API key."""


@dataclass(frozen=True)
class GeneratedMedia:
    data: bytes
    content_type: str


class GeminiMediaService:
    def __init__(self, settings: Settings):
        self._image_model = settings.gemini_image_model
        self._video_model = settings.gemini_video_model
        self._client = genai.Client(
            api_key=settings.gemini_api_key.get_secret_value(),
            http_options=types.HttpOptions(timeout=int(settings.gemini_media_timeout_s * 1000)),
        )

    @property
    def image_model(self) -> str:
        return self._image_model

    @property
    def video_model(self) -> str:
        return self._video_model

    def generate_image(self, prompt: str) -> GeneratedMedia:
        try:
            response = self._client.models.generate_content(
                model=self._image_model,
                contents=prompt,
                config=types.GenerateContentConfig(response_modalities=["IMAGE"]),
            )
        except errors.APIError as exc:
            raise MediaGenerationError(f"image generation failed ({exc.code})") from None
        parts = response.candidates[0].content.parts if response.candidates else []
        images = [part for part in parts if part.inline_data]
        if not images:
            raise MediaGenerationError("no image was returned, possibly blocked by the safety filter")
        return GeneratedMedia(data=images[0].inline_data.data, content_type=images[0].inline_data.mime_type)

    def generate_video(self, prompt: str, *, aspect_ratio: str = "9:16") -> GeneratedMedia:
        try:
            interaction = self._client.interactions.create(
                model=self._video_model,
                input=prompt,
                response_format={"type": "video", "aspect_ratio": aspect_ratio, "resolution": "720p"},
            )
        except errors.APIError as exc:
            raise MediaGenerationError(f"video generation failed ({exc.code})") from None
        video = getattr(interaction, "output_video", None)
        if video is None:
            raise MediaGenerationError("no video was returned, possibly blocked by the safety filter")
        if getattr(video, "data", None):
            return GeneratedMedia(data=base64.b64decode(video.data), content_type="video/mp4")
        if getattr(video, "uri", None):
            return GeneratedMedia(data=self._download(video.uri), content_type="video/mp4")
        raise MediaGenerationError("the video response had an unexpected shape")

    def _download(self, uri: str) -> bytes:
        file_name = uri.split("/")[-1]
        deadline = time.monotonic() + MAX_POLL_SECONDS
        while True:
            state = self._client.files.get(name=f"files/{file_name}").state.name
            if state == "ACTIVE":
                break
            if state == "FAILED":
                raise MediaGenerationError("the video file failed to process")
            if time.monotonic() > deadline:
                raise MediaGenerationError("timed out waiting for the video file")
            time.sleep(5)
        return self._client.files.download(file=uri)


@lru_cache
def get_media_service() -> GeminiMediaService:
    return GeminiMediaService(get_settings())
