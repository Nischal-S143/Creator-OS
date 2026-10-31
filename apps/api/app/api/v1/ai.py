import logging
from hmac import compare_digest
from typing import Literal

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field

from app.core.config import get_settings
from app.integrations.gemini.service import (
    GeminiInvalidResponseError,
    GeminiRequestError,
    GeminiService,
    GeminiUnavailableError,
    get_gemini,
)

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/ai", tags=["ai"])


class ContentIdea(BaseModel):
    title: str = Field(min_length=3, max_length=120)
    description: str = Field(min_length=10, max_length=500)
    format: Literal["video", "reel", "carousel", "post", "story", "article", "other"]


class ContentIdeas(BaseModel):
    ideas: list[ContentIdea] = Field(min_length=3, max_length=3)


class TestRequest(BaseModel):
    prompt: str = Field(
        default="Create three content ideas for a fitness brand.", min_length=1, max_length=2000
    )


class TestResponse(BaseModel):
    model: str
    result: ContentIdeas


def require_internal_key(x_internal_key: str = Header(default="")) -> None:
    configured = get_settings().internal_api_key
    expected = configured.get_secret_value() if configured else ""
    if not expected or not compare_digest(x_internal_key.encode(), expected.encode()):
        raise HTTPException(status_code=403, detail="forbidden")


@router.post("/test", response_model=TestResponse, dependencies=[Depends(require_internal_key)])
async def ai_test(
    body: TestRequest | None = None, gemini: GeminiService = Depends(get_gemini)
) -> TestResponse:
    prompt = (body or TestRequest()).prompt
    try:
        result = await gemini.generate_json(
            prompt,
            ContentIdeas,
            system="You are a content strategist. Return exactly three ideas.",
        )
    except GeminiUnavailableError as exc:
        raise HTTPException(status_code=503, detail="AI service temporarily unavailable") from exc
    except GeminiInvalidResponseError as exc:
        raise HTTPException(status_code=502, detail="AI returned an invalid response") from exc
    except GeminiRequestError as exc:
        log.warning("gemini request rejected: %s", exc)
        raise HTTPException(status_code=502, detail="AI request failed") from exc
    return TestResponse(model=gemini.model, result=result)
