import logging
import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, StringConstraints
from sqlalchemy.orm import Session

from app.agents.specialists import Model, audience_agent, simulator_agent
from app.api.v1.brand_brain import enforce_ai_limit, finish_run, get_brand_or_404, start_run
from app.api.v1.campaigns import CampaignDetail, CampaignOut, _detail, _get_campaign
from app.db.session import get_db
from app.integrations.gemini.bridge import get_gateway
from app.integrations.gemini.service import GeminiError
from app.integrations.meko.client import MekoClient, get_meko
from app.models import Campaign
from app.schemas.core import Request
from app.security.context import TenantContext, require
from app.security.permissions import Permission
from app.services.brand_context import AgentLog, NoApprovedProfile, load_brand_context
from app.services.intelligence import (
    CRITERIA_WEIGHTS,
    clean_comments,
    score_clusters,
    score_strategy,
)

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/organizations/{org_id}/brands/{brand_id}", tags=["intelligence"])


class SelectStrategy(Request):
    index: int = Field(ge=0, le=5)


class AudienceInput(Request):
    comments: Annotated[str, StringConstraints(min_length=3, max_length=100_000)]


class FromTopic(Request):
    topic_index: int = Field(ge=0, le=20)


class AudienceReportOut(BaseModel):
    report: dict | None


def _context(db: Session, meko: MekoClient | None, tenant: TenantContext, brand_id: uuid.UUID, query: str):
    try:
        return load_brand_context(db, meko, tenant.organization_id, brand_id, query)
    except NoApprovedProfile as exc:
        raise HTTPException(status_code=409, detail="approve a brand profile first") from exc


@router.post("/campaigns/{campaign_id}/simulate", response_model=CampaignDetail)
def simulate(
    brand_id: uuid.UUID,
    campaign_id: uuid.UUID,
    tenant: TenantContext = Depends(require(Permission.CAMPAIGN_EDIT)),
    db: Session = Depends(get_db),
    model: Model = Depends(get_gateway),
    meko: MekoClient | None = Depends(get_meko),
) -> CampaignDetail:
    campaign = _get_campaign(db, tenant, brand_id, campaign_id)
    context = _context(db, meko, tenant, brand_id, f"{campaign.objective} strategy lessons")
    enforce_ai_limit(db, tenant.organization_id)
    run = start_run(db, tenant, brand_id, "flight_simulator", model.model, campaign_id=campaign.id)
    try:
        result = simulator_agent(
            model,
            campaign={"name": campaign.name, "objective": campaign.objective, "audience": campaign.audience},
            brand=context.data,
        )
    except GeminiError as exc:
        log.warning("flight simulator failed: %s", exc)
        finish_run(db, run, error=type(exc).__name__)
        raise HTTPException(status_code=502, detail="AI could not finish this. Try again.") from exc
    strategies = sorted(
        ({**item.model_dump(), "total_score": score_strategy(item)} for item in result.strategies),
        key=lambda item: item["total_score"],
        reverse=True,
    )
    campaign.simulation = {
        "strategies": strategies,
        "selected": None,
        "weights": CRITERIA_WEIGHTS,
        "limitations": result.limitations,
        "model": model.model,
        "created_at": datetime.now(UTC).isoformat(),
    }
    db.commit()
    finish_run(db, run, detail={"strategies": len(strategies)})
    AgentLog(meko, context.datapack_id, f"Flight Simulator: {campaign.id}").record(
        "Flight Simulator", "compare campaign strategies", result.model_dump_json()
    )
    return _detail(db, campaign)


@router.post("/campaigns/{campaign_id}/simulation/select", response_model=CampaignDetail)
def select_strategy(
    brand_id: uuid.UUID,
    campaign_id: uuid.UUID,
    body: SelectStrategy,
    tenant: TenantContext = Depends(require(Permission.CAMPAIGN_EDIT)),
    db: Session = Depends(get_db),
) -> CampaignDetail:
    campaign = _get_campaign(db, tenant, brand_id, campaign_id)
    simulation = campaign.simulation
    if not simulation or body.index >= len(simulation["strategies"]):
        raise HTTPException(status_code=404, detail="strategy not found")
    campaign.simulation = {**simulation, "selected": body.index}
    db.commit()
    return _detail(db, campaign)


@router.get("/audience", response_model=AudienceReportOut)
def get_audience(
    brand_id: uuid.UUID,
    tenant: TenantContext = Depends(require(Permission.CAMPAIGN_VIEW)),
    db: Session = Depends(get_db),
) -> AudienceReportOut:
    return AudienceReportOut(report=get_brand_or_404(db, tenant, brand_id).audience_report)


@router.post("/audience/analyze", response_model=AudienceReportOut)
def analyze_audience(
    brand_id: uuid.UUID,
    body: AudienceInput,
    tenant: TenantContext = Depends(require(Permission.CAMPAIGN_EDIT)),
    db: Session = Depends(get_db),
    model: Model = Depends(get_gateway),
    meko: MekoClient | None = Depends(get_meko),
) -> AudienceReportOut:
    """Raw comments are analyzed but never stored, and they stay off Meko's memory-extraction side."""
    brand = get_brand_or_404(db, tenant, brand_id)
    comments, removed = clean_comments(body.comments)
    if len(comments) < 3:
        raise HTTPException(status_code=422, detail="paste at least 3 different comments, one per line")
    context = _context(db, meko, tenant, brand_id, "audience questions topics")
    enforce_ai_limit(db, tenant.organization_id)
    run = start_run(db, tenant, brand_id, "audience_intelligence", model.model)
    try:
        result = audience_agent(model, comments=comments, brand=context.data)
    except GeminiError as exc:
        log.warning("audience analysis failed: %s", exc)
        finish_run(db, run, error=type(exc).__name__)
        raise HTTPException(status_code=502, detail="AI could not finish this. Try again.") from exc
    report = {
        "topics": score_clusters(result.clusters, len(comments)),
        "comments_analyzed": len(comments),
        "comments_removed": removed,
        "limitations": result.limitations,
        "source": "pasted by a person",
        "model": model.model,
        "created_at": datetime.now(UTC).isoformat(),
    }
    brand.audience_report = report
    db.commit()
    finish_run(db, run, detail={"topics": len(report["topics"]), "comments": len(comments)})
    AgentLog(meko, context.datapack_id, f"Audience Intelligence: {brand.id}").record(
        "Audience Intelligence",
        "cluster audience comments into topics",
        str({key: report[key] for key in ("topics", "comments_analyzed")}),
    )
    return AudienceReportOut(report=report)


@router.post("/audience/campaign", response_model=CampaignOut, status_code=201)
def campaign_from_topic(
    brand_id: uuid.UUID,
    body: FromTopic,
    tenant: TenantContext = Depends(require(Permission.CAMPAIGN_EDIT)),
    db: Session = Depends(get_db),
) -> Campaign:
    """A person choosing a topic is the approval step: nothing becomes a campaign on its own."""
    brand = get_brand_or_404(db, tenant, brand_id)
    topics = (brand.audience_report or {}).get("topics", [])
    if body.topic_index >= len(topics):
        raise HTTPException(status_code=404, detail="topic not found")
    topic = topics[body.topic_index]
    campaign = Campaign(
        organization_id=tenant.organization_id,
        brand_id=brand_id,
        name=topic["topic"][:200],
        objective=topic["suggested_angle"][:2000],
        created_by=tenant.user.id,
    )
    db.add(campaign)
    db.commit()
    return campaign
