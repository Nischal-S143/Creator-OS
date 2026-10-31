"""Shapes the model must return. Gemini output is validated against these before use."""

from pydantic import BaseModel, Field


class BrandProfileDraft(BaseModel):
    voice: str = Field(min_length=3, max_length=1500)
    tone: str = Field(min_length=3, max_length=1500)
    audience: str = Field(min_length=3, max_length=1500)
    content_pillars: list[str] = Field(min_length=1, max_length=8)
    restrictions: list[str] = Field(max_length=20)


class CampaignIdeaDraft(BaseModel):
    title: str = Field(min_length=3, max_length=200)
    hook: str = Field(min_length=3, max_length=600)
    description: str = Field(min_length=10, max_length=1500)
    platform: str = Field(min_length=2, max_length=50)
    content_format: str = Field(min_length=2, max_length=50)


class CampaignIdeasDraft(BaseModel):
    ideas: list[CampaignIdeaDraft] = Field(min_length=3, max_length=3)
