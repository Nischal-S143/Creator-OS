"""Typed outputs for each agent. Gemini output is validated against these before anything uses it."""

from typing import Literal

from pydantic import BaseModel, Field


class ResearchBrief(BaseModel):
    audience_questions: list[str] = Field(max_length=8)
    competitor_themes: list[str] = Field(max_length=8)
    angles: list[str] = Field(min_length=1, max_length=6)
    claims_to_verify: list[str] = Field(max_length=10)
    limitations: list[str] = Field(min_length=1, max_length=6)


class ScriptDraft(BaseModel):
    hook: str = Field(min_length=3, max_length=500)
    script: str = Field(min_length=10, max_length=8000)
    caption: str = Field(min_length=3, max_length=2200)
    cta: str = Field(min_length=2, max_length=300)
    hashtags: list[str] = Field(max_length=15)


class Scene(BaseModel):
    purpose: str = Field(min_length=2, max_length=300)
    visual_description: str = Field(min_length=3, max_length=800)
    on_screen_text: str = Field(max_length=300)
    duration_seconds: int = Field(ge=1, le=120)


class ScenePlan(BaseModel):
    scenes: list[Scene] = Field(min_length=1, max_length=20)


class GuardianFinding(BaseModel):
    check_type: Literal["voice", "restrictions", "claims", "platform_policy"]
    severity: Literal["info", "warning", "blocker"]
    evidence: str = Field(min_length=1, max_length=800)
    recommendation: str = Field(min_length=1, max_length=800)


class GuardianResult(BaseModel):
    findings: list[GuardianFinding] = Field(max_length=25)


class MarketGap(BaseModel):
    topic: str = Field(min_length=2, max_length=200)
    why_it_may_be_open: str = Field(min_length=5, max_length=800)
    evidence_to_collect: list[str] = Field(min_length=1, max_length=6)
    confidence: Literal["low", "medium"]


class MarketGapReport(BaseModel):
    gaps: list[MarketGap] = Field(min_length=1, max_length=6)
    limitations: list[str] = Field(min_length=1, max_length=6)


class FeedbackHypothesis(BaseModel):
    observation: str = Field(min_length=5, max_length=600)
    hypothesis: str = Field(min_length=5, max_length=600)
    suggested_experiment: str = Field(min_length=5, max_length=600)
    confidence: Literal["low", "medium"]


class FeedbackReportDraft(BaseModel):
    summary: str = Field(min_length=5, max_length=1000)
    hypotheses: list[FeedbackHypothesis] = Field(max_length=5)


class Rating(BaseModel):
    score: int = Field(ge=1, le=5)
    reason: str = Field(min_length=3, max_length=500)


class Ratings(BaseModel):
    brand_fit: Rating
    audience_relevance: Rating
    feasibility: Rating
    differentiation: Rating
    risk_safety: Rating
    evidence_quality: Rating


class StrategyDraft(BaseModel):
    name: str = Field(min_length=2, max_length=150)
    summary: str = Field(min_length=5, max_length=800)
    target_audience: str = Field(min_length=2, max_length=500)
    content_pillars: list[str] = Field(min_length=1, max_length=6)
    hook_strategy: str = Field(min_length=3, max_length=500)
    production_effort: Literal["low", "medium", "high"]
    ratings: Ratings
    assumptions: list[str] = Field(min_length=1, max_length=8)
    evidence: list[str] = Field(max_length=8)
    risks: list[str] = Field(min_length=1, max_length=8)


class SimulationDraft(BaseModel):
    strategies: list[StrategyDraft] = Field(min_length=3, max_length=3)
    limitations: list[str] = Field(min_length=1, max_length=6)


class AudienceCluster(BaseModel):
    topic: str = Field(min_length=2, max_length=150)
    intent: Literal["learn", "buy", "compare", "complain", "praise", "other"]
    sentiment: Literal["positive", "neutral", "negative", "mixed"]
    # No length cap: Gemini rejects this schema with one, and score_clusters validates every number.
    comment_numbers: list[int] = Field(min_length=1)
    representative_questions: list[str] = Field(max_length=5)
    brand_relevance: int = Field(ge=1, le=5)
    content_gap: bool
    suggested_angle: str = Field(min_length=5, max_length=500)


class AudienceReportDraft(BaseModel):
    clusters: list[AudienceCluster] = Field(min_length=1, max_length=12)
    limitations: list[str] = Field(min_length=1, max_length=6)
