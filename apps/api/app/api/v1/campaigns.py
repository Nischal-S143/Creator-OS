import logging
import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, StringConstraints
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.api.v1.brand_brain import enforce_ai_limit, finish_run, get_brand_or_404, start_run
from app.db.session import get_db
from app.graphs.campaign_graph import build_campaign_graph
from app.integrations.gemini.bridge import GeminiGateway, get_gateway
from app.integrations.gemini.service import GeminiError
from app.integrations.meko.client import MekoClient, get_meko
from app.models import AgentRun, BrandProfile, Campaign, CampaignScenario
from app.schemas.core import Name, Request, Response
from app.security.context import TenantContext, require
from app.security.permissions import Permission

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/organizations/{org_id}/brands/{brand_id}/campaigns", tags=["campaigns"])

LongText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=2000)]


class CampaignCreate(Request):
    name: Name
    objective: LongText
    audience: LongText | None = None


class CampaignOut(Response):
    id: uuid.UUID
    brand_id: uuid.UUID
    name: str
    objective: str
    audience: str | None
    created_at: datetime


class ScenarioOut(Response):
    id: uuid.UUID
    agent_run_id: uuid.UUID
    title: str
    hook: str
    description: str
    platform: str
    content_format: str
    selected: bool


class RunOut(Response):
    id: uuid.UUID
    graph_name: str
    status: str
    model: str | None
    error: str | None
    detail: dict
    started_at: datetime
    finished_at: datetime | None


class CampaignDetail(CampaignOut):
    scenarios: list[ScenarioOut]
    runs: list[RunOut]


class CampaignList(BaseModel):
    items: list[CampaignOut]


def _get_campaign(
    db: Session, tenant: TenantContext, brand_id: uuid.UUID, campaign_id: uuid.UUID
) -> Campaign:
    campaign = db.scalar(
        select(Campaign).where(
            Campaign.id == campaign_id,
            Campaign.organization_id == tenant.organization_id,
            Campaign.brand_id == brand_id,
        )
    )
    if campaign is None:
        raise HTTPException(status_code=404, detail="campaign not found")
    return campaign


def _detail(db: Session, campaign: Campaign) -> CampaignDetail:
    runs = list(
        db.scalars(
            select(AgentRun)
            .where(AgentRun.organization_id == campaign.organization_id, AgentRun.campaign_id == campaign.id)
            .order_by(AgentRun.started_at.desc())
            .limit(20)
        )
    )
    latest = next((run for run in runs if run.status == "succeeded"), None)
    scenarios = (
        db.scalars(
            select(CampaignScenario)
            .where(
                CampaignScenario.organization_id == campaign.organization_id,
                CampaignScenario.campaign_id == campaign.id,
                CampaignScenario.agent_run_id == latest.id,
            )
            .order_by(CampaignScenario.created_at, CampaignScenario.title)
        ).all()
        if latest
        else []
    )
    return CampaignDetail(
        **CampaignOut.model_validate(campaign).model_dump(),
        scenarios=[ScenarioOut.model_validate(row) for row in scenarios],
        runs=[RunOut.model_validate(row) for row in runs],
    )


@router.post("", response_model=CampaignOut, status_code=201)
def create_campaign(
    brand_id: uuid.UUID,
    body: CampaignCreate,
    tenant: TenantContext = Depends(require(Permission.CAMPAIGN_EDIT)),
    db: Session = Depends(get_db),
) -> Campaign:
    get_brand_or_404(db, tenant, brand_id)
    campaign = Campaign(
        organization_id=tenant.organization_id,
        brand_id=brand_id,
        name=body.name,
        objective=body.objective,
        audience=body.audience,
        created_by=tenant.user.id,
    )
    db.add(campaign)
    db.commit()
    return campaign


@router.get("", response_model=CampaignList)
def list_campaigns(
    brand_id: uuid.UUID,
    tenant: TenantContext = Depends(require(Permission.CAMPAIGN_VIEW)),
    db: Session = Depends(get_db),
) -> CampaignList:
    get_brand_or_404(db, tenant, brand_id)
    rows = db.scalars(
        select(Campaign)
        .where(Campaign.organization_id == tenant.organization_id, Campaign.brand_id == brand_id)
        .order_by(Campaign.created_at.desc())
        .limit(100)
    )
    return CampaignList(items=[CampaignOut.model_validate(row) for row in rows])


@router.get("/{campaign_id}", response_model=CampaignDetail)
def get_campaign(
    brand_id: uuid.UUID,
    campaign_id: uuid.UUID,
    tenant: TenantContext = Depends(require(Permission.CAMPAIGN_VIEW)),
    db: Session = Depends(get_db),
) -> CampaignDetail:
    return _detail(db, _get_campaign(db, tenant, brand_id, campaign_id))


@router.post("/{campaign_id}/generate", response_model=CampaignDetail)
def generate_ideas(
    brand_id: uuid.UUID,
    campaign_id: uuid.UUID,
    tenant: TenantContext = Depends(require(Permission.CAMPAIGN_EDIT)),
    db: Session = Depends(get_db),
    gemini: GeminiGateway = Depends(get_gateway),
    meko: MekoClient | None = Depends(get_meko),
) -> CampaignDetail:
    campaign = _get_campaign(db, tenant, brand_id, campaign_id)
    approved = db.scalar(
        select(BrandProfile.id).where(
            BrandProfile.organization_id == tenant.organization_id,
            BrandProfile.brand_id == brand_id,
            BrandProfile.status == "approved",
        )
    )
    if approved is None:
        raise HTTPException(status_code=409, detail="approve a brand profile before generating ideas")
    enforce_ai_limit(db, tenant.organization_id)
    run = start_run(db, tenant, brand_id, "campaign_ideas", gemini.model, campaign_id=campaign.id)
    graph = build_campaign_graph(db, gemini, meko, campaign=campaign, run_id=run.id)
    try:
        # One worker thread keeps the database session on a single thread at a time.
        state = graph.invoke({}, {"max_concurrency": 1})
    except GeminiError as exc:
        log.warning("campaign idea generation failed: %s", exc)
        db.rollback()
        finish_run(db, run, error=type(exc).__name__)
        raise HTTPException(status_code=502, detail="AI could not generate ideas. Try again.") from exc
    finish_run(db, run, detail={"memory_used": state["memory_used"], "memories": len(state["memories"])})
    return _detail(db, campaign)


@router.post("/{campaign_id}/scenarios/{scenario_id}/select", response_model=CampaignDetail)
def select_scenario(
    brand_id: uuid.UUID,
    campaign_id: uuid.UUID,
    scenario_id: uuid.UUID,
    tenant: TenantContext = Depends(require(Permission.CAMPAIGN_EDIT)),
    db: Session = Depends(get_db),
) -> CampaignDetail:
    campaign = _get_campaign(db, tenant, brand_id, campaign_id)
    scope = (
        CampaignScenario.organization_id == tenant.organization_id,
        CampaignScenario.campaign_id == campaign.id,
    )
    scenario = db.scalar(select(CampaignScenario).where(CampaignScenario.id == scenario_id, *scope))
    if scenario is None:
        raise HTTPException(status_code=404, detail="idea not found")
    db.execute(update(CampaignScenario).where(*scope).values(selected=False))
    scenario.selected = True
    db.commit()
    return _detail(db, campaign)
