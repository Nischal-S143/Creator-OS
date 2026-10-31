"""Publishing records, results, the Feedback Agent and the Learning Ledger.

Publishing is recorded by a person after posting, because no platform is connected yet. The approval checks
are the same ones an automated publisher must pass.
"""

import logging
import uuid
from datetime import UTC, datetime, timedelta
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import AnyHttpUrl, BaseModel, Field, StringConstraints
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents.specialists import Model, feedback_agent
from app.api.v1.brand_brain import get_brand_or_404
from app.db.session import get_db
from app.graphs.content_graph import latest_version
from app.integrations.gemini.bridge import get_gateway
from app.integrations.gemini.service import GeminiError
from app.integrations.meko.client import MekoClient, MekoError, get_meko
from app.models import (
    AgentRun,
    Approval,
    Brand,
    Campaign,
    CampaignScenario,
    ContentItem,
    GuardianReview,
)
from app.schemas.core import Request
from app.security.context import TenantContext, require
from app.security.permissions import Permission
from app.services.brand_context import AgentLog
from app.services.performance import METRICS, MIN_SAMPLE, compare_to_baseline

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/organizations/{org_id}", tags=["learning"])

LESSON_REVIEW_DAYS = 90
Count = Annotated[int, Field(ge=0, le=10_000_000_000)]


class Schedule(Request):
    scheduled_for: datetime


class RecordPublished(Request):
    url: AnyHttpUrl
    published_at: datetime | None = None


class Results(Request):
    window: Literal["48h", "7d", "30d"]
    views: Count | None = None
    reach: Count | None = None
    likes: Count | None = None
    comments: Count | None = None
    shares: Count | None = None
    saves: Count | None = None


class LessonDecision(Request):
    approve: bool
    text: Annotated[str, StringConstraints(strip_whitespace=True, min_length=5, max_length=600)] | None = None


class CalendarItem(BaseModel):
    content_id: uuid.UUID
    brand_id: uuid.UUID
    brand_name: str
    title: str
    platform: str
    kind: str
    status: str
    version: int
    scheduled_for: str | None
    published_at: str | None
    url: str | None
    windows_reported: list[str]


class CalendarList(BaseModel):
    items: list[CalendarItem]


class Report(BaseModel):
    window: str
    entered: dict
    comparison: dict
    summary: str | None
    ai_available: bool
    hypotheses: list[dict]
    recorded_at: str


class LessonList(BaseModel):
    items: list[dict]


def _item(db: Session, tenant: TenantContext, content_id: uuid.UUID) -> ContentItem:
    item = db.scalar(
        select(ContentItem).where(
            ContentItem.id == content_id, ContentItem.organization_id == tenant.organization_id
        )
    )
    if item is None:
        raise HTTPException(status_code=404, detail="content not found")
    return item


def require_approved_version(db: Session, item: ContentItem) -> Approval:
    """Everything that leads to publishing passes here: exact version, exact fingerprint, human approval."""
    version = latest_version(db, item)
    approval = db.scalar(
        select(Approval).where(
            Approval.organization_id == item.organization_id,
            Approval.content_id == item.id,
            Approval.content_version == item.current_version,
            Approval.decision == "approved",
        )
    )
    if (
        item.status != "approved"
        or version is None
        or approval is None
        or approval.content_hash != version.content_hash
    ):
        raise HTTPException(
            status_code=409, detail="only content approved in its current version can publish"
        )
    return approval


@router.post("/content/{content_id}/schedule", response_model=CalendarItem)
def schedule(
    content_id: uuid.UUID,
    body: Schedule,
    tenant: TenantContext = Depends(require(Permission.CONTENT_APPROVE)),
    db: Session = Depends(get_db),
) -> CalendarItem:
    item = _item(db, tenant, content_id)
    require_approved_version(db, item)
    if (item.publication or {}).get("published_at"):
        raise HTTPException(status_code=409, detail="this content is already published")
    item.publication = {
        **(item.publication or {}),
        "scheduled_for": body.scheduled_for.astimezone(UTC).isoformat(),
        "version": item.current_version,
    }
    db.commit()
    return _calendar_item(db, item)


@router.post("/content/{content_id}/published", response_model=CalendarItem)
def record_published(
    content_id: uuid.UUID,
    body: RecordPublished,
    tenant: TenantContext = Depends(require(Permission.CONTENT_APPROVE)),
    db: Session = Depends(get_db),
) -> CalendarItem:
    item = _item(db, tenant, content_id)
    approval = require_approved_version(db, item)
    item.publication = {
        **(item.publication or {}),
        "published_at": (body.published_at or datetime.now(UTC)).astimezone(UTC).isoformat(),
        "url": str(body.url),
        "version": item.current_version,
        "content_hash": approval.content_hash,
        "method": "recorded_by_person",
        "recorded_by": str(tenant.user.id),
    }
    db.commit()
    return _calendar_item(db, item)


def _calendar_item(db: Session, item: ContentItem, brand_name: str | None = None) -> CalendarItem:
    publication = item.publication or {}
    name = brand_name or db.scalar(
        select(Brand.name).where(Brand.organization_id == item.organization_id, Brand.id == item.brand_id)
    )
    return CalendarItem(
        content_id=item.id,
        brand_id=item.brand_id,
        brand_name=name,
        title=item.title,
        platform=item.platform,
        kind=item.kind,
        status=item.status,
        version=item.current_version,
        scheduled_for=publication.get("scheduled_for"),
        published_at=publication.get("published_at"),
        url=publication.get("url"),
        windows_reported=sorted((item.performance or {}).keys()),
    )


@router.get("/calendar", response_model=CalendarList)
def calendar(
    tenant: TenantContext = Depends(require(Permission.CAMPAIGN_VIEW)),
    db: Session = Depends(get_db),
) -> CalendarList:
    rows = db.execute(
        select(ContentItem, Brand.name)
        .join(
            Brand,
            (Brand.id == ContentItem.brand_id) & (Brand.organization_id == ContentItem.organization_id),
        )
        .where(ContentItem.organization_id == tenant.organization_id, ContentItem.status == "approved")
        .order_by(ContentItem.updated_at.desc())
        .limit(200)
    ).all()
    return CalendarList(items=[_calendar_item(db, item, name) for item, name in rows])


@router.get("/content/{content_id}/results")
def get_results(
    content_id: uuid.UUID,
    tenant: TenantContext = Depends(require(Permission.CAMPAIGN_VIEW)),
    db: Session = Depends(get_db),
) -> dict:
    return _item(db, tenant, content_id).performance or {}


@router.post("/content/{content_id}/results", response_model=Report)
def enter_results(
    content_id: uuid.UUID,
    body: Results,
    tenant: TenantContext = Depends(require(Permission.CAMPAIGN_EDIT)),
    db: Session = Depends(get_db),
    model: Model = Depends(get_gateway),
    meko: MekoClient | None = Depends(get_meko),
) -> Report:
    """The comparison is always code. If AI is unavailable, the measured report still stands."""
    item = _item(db, tenant, content_id)
    if not (item.publication or {}).get("published_at"):
        raise HTTPException(status_code=409, detail="record the post as published first")
    entered = {name: getattr(body, name) for name in METRICS if getattr(body, name) is not None}
    if not entered:
        raise HTTPException(status_code=422, detail="enter at least one number")
    siblings = db.scalars(
        select(ContentItem).where(
            ContentItem.organization_id == tenant.organization_id,
            ContentItem.brand_id == item.brand_id,
            ContentItem.id != item.id,
        )
    ).all()
    others = [
        sibling.performance[body.window]["entered"]
        for sibling in siblings
        if (sibling.performance or {}).get(body.window)
    ]
    comparison = compare_to_baseline(entered, others)
    brand = get_brand_or_404(db, tenant, item.brand_id)
    version = latest_version(db, item)
    summary, hypotheses, ai_available = None, [], True
    try:
        draft = feedback_agent(
            model,
            content={
                "title": item.title,
                "platform": item.platform,
                "hook": version.hook,
                "cta": version.cta,
            },
            brand={"name": brand.name},
            measured=comparison,
        )
        summary = draft.summary
        hypotheses = [entry.model_dump() for entry in draft.hypotheses]
    except GeminiError as exc:
        log.warning("feedback agent unavailable: %s", exc)
        ai_available = False
    report = {
        "window": body.window,
        "entered": entered,
        "comparison": comparison,
        "summary": summary,
        "ai_available": ai_available,
        "hypotheses": hypotheses,
        "recorded_at": datetime.now(UTC).isoformat(),
    }
    item.performance = {**(item.performance or {}), body.window: report}
    now = datetime.now(UTC).isoformat()
    proposed = [
        {
            "id": str(uuid.uuid4()),
            "status": "proposed",
            "text": entry["hypothesis"],
            "observation": entry["observation"],
            "suggested_experiment": entry["suggested_experiment"],
            # One post is thin evidence, so confidence stays low until the brand has enough history.
            "confidence": entry["confidence"] if comparison["sample_size"] >= MIN_SAMPLE else "low",
            "sample_size": comparison["sample_size"],
            "source_content_id": str(item.id),
            "source_title": item.title,
            "window": body.window,
            "created_at": now,
        }
        for entry in hypotheses
    ]
    if proposed:
        brand.lessons = [*(brand.lessons or []), *proposed]
    db.commit()
    datapack_id = (meko.shared_datapack_id or brand.meko_datapack_id) if meko else None
    AgentLog(meko, datapack_id, f"Feedback: {item.title} ({item.id})").record(
        "Analytics and Feedback", f"review results at {body.window}", str(report)
    )
    return Report(**report)


@router.get("/brands/{brand_id}/lessons", response_model=LessonList)
def list_lessons(
    brand_id: uuid.UUID,
    tenant: TenantContext = Depends(require(Permission.CAMPAIGN_VIEW)),
    db: Session = Depends(get_db),
) -> LessonList:
    return LessonList(items=list(reversed(get_brand_or_404(db, tenant, brand_id).lessons or [])))


@router.post("/brands/{brand_id}/lessons/{lesson_id}/decision", response_model=LessonList)
def decide_lesson(
    brand_id: uuid.UUID,
    lesson_id: str,
    body: LessonDecision,
    tenant: TenantContext = Depends(require(Permission.PROFILE_APPROVE)),
    db: Session = Depends(get_db),
    meko: MekoClient | None = Depends(get_meko),
) -> LessonList:
    """A person decides. Only approved lessons reach future campaigns, each with a review date."""
    brand = get_brand_or_404(db, tenant, brand_id)
    lessons = [dict(entry) for entry in brand.lessons or []]
    lesson = next((entry for entry in lessons if entry["id"] == lesson_id), None)
    if lesson is None:
        raise HTTPException(status_code=404, detail="lesson not found")
    if lesson["status"] != "proposed":
        raise HTTPException(status_code=409, detail="this lesson has already been decided")
    now = datetime.now(UTC)
    lesson["status"] = "approved" if body.approve else "rejected"
    lesson["decided_by"] = str(tenant.user.id)
    lesson["decided_at"] = now.isoformat()
    if body.text:
        lesson["text"] = body.text
    if body.approve:
        lesson["review_at"] = (now + timedelta(days=LESSON_REVIEW_DAYS)).isoformat()
    brand.lessons = lessons
    db.commit()
    datapack_id = (meko.shared_datapack_id or brand.meko_datapack_id) if meko else None
    if body.approve and meko and datapack_id:
        try:
            meko.add_memory(
                datapack_id,
                f"Approved lesson for {brand.name}: {lesson['text']} "
                f"(from '{lesson['source_title']}', based on {lesson['sample_size']} comparison posts).",
                {"source": "approved_lesson", "lesson_id": lesson_id, "brand_id": str(brand.id)},
            )
        except MekoError as exc:
            # The ledger in YugabyteDB is authoritative, and campaigns read approved lessons from it directly.
            log.warning("meko lesson sync failed: %s", exc)
    return LessonList(items=list(reversed(lessons)))


class ReportContent(BaseModel):
    id: uuid.UUID
    title: str
    kind: str
    status: str
    version: int
    guardian_status: str | None
    published_at: str | None
    url: str | None
    reviews: list[dict]


class CampaignReport(BaseModel):
    id: uuid.UUID
    name: str
    objective: str
    strategy: dict | None
    selected_idea: str | None
    lessons_used: list[dict]
    content: list[ReportContent]
    lessons_learned: list[dict]


@router.get("/brands/{brand_id}/campaigns/{campaign_id}/report", response_model=CampaignReport)
def campaign_report(
    brand_id: uuid.UUID,
    campaign_id: uuid.UUID,
    tenant: TenantContext = Depends(require(Permission.CAMPAIGN_VIEW)),
    db: Session = Depends(get_db),
) -> CampaignReport:
    brand = get_brand_or_404(db, tenant, brand_id)
    campaign = db.scalar(
        select(Campaign).where(
            Campaign.id == campaign_id,
            Campaign.organization_id == tenant.organization_id,
            Campaign.brand_id == brand_id,
        )
    )
    if campaign is None:
        raise HTTPException(status_code=404, detail="campaign not found")
    simulation = campaign.simulation or {}
    selected = simulation.get("selected")
    strategy = simulation["strategies"][selected] if selected is not None else None
    idea = db.scalar(
        select(CampaignScenario.title).where(
            CampaignScenario.organization_id == tenant.organization_id,
            CampaignScenario.campaign_id == campaign.id,
            CampaignScenario.selected.is_(True),
        )
    )
    latest_run = db.scalar(
        select(AgentRun)
        .where(
            AgentRun.organization_id == tenant.organization_id,
            AgentRun.campaign_id == campaign.id,
            AgentRun.graph_name == "campaign_ideas",
            AgentRun.status == "succeeded",
        )
        .order_by(AgentRun.started_at.desc())
    )
    items = db.scalars(
        select(ContentItem)
        .where(
            ContentItem.organization_id == tenant.organization_id,
            ContentItem.campaign_id == campaign.id,
        )
        .order_by(ContentItem.created_at)
    ).all()
    content = []
    for item in items:
        verdict = db.scalar(
            select(GuardianReview.status)
            .where(
                GuardianReview.organization_id == tenant.organization_id,
                GuardianReview.content_id == item.id,
                GuardianReview.content_version == item.current_version,
            )
            .order_by(GuardianReview.created_at.desc())
        )
        publication = item.publication or {}
        content.append(
            ReportContent(
                id=item.id,
                title=item.title,
                kind=item.kind,
                status=item.status,
                version=item.current_version,
                guardian_status=verdict,
                published_at=publication.get("published_at"),
                url=publication.get("url"),
                reviews=[
                    {"window": window, "metrics": report["comparison"]["metrics"]}
                    for window, report in (item.performance or {}).items()
                ],
            )
        )
    ids = {str(item.id) for item in items}
    return CampaignReport(
        id=campaign.id,
        name=campaign.name,
        objective=campaign.objective,
        strategy=None
        if strategy is None
        else {"name": strategy["name"], "total_score": strategy["total_score"]},
        selected_idea=idea,
        lessons_used=(latest_run.detail or {}).get("lessons_used", []) if latest_run else [],
        content=content,
        lessons_learned=[entry for entry in brand.lessons or [] if entry.get("source_content_id") in ids],
    )
