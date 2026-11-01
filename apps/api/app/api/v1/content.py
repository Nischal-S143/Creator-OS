import logging
import uuid
from datetime import UTC, datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response as RawResponse
from langgraph.types import Command
from pydantic import BaseModel, Field, StringConstraints
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.agents.specialists import Model, market_gap_agent
from app.api.v1.brand_brain import enforce_ai_limit, finish_run, get_brand_or_404, start_run
from app.db.session import get_db
from app.graphs.checkpoints import checkpointer
from app.graphs.content_graph import (
    add_version,
    build_content_graph,
    content_hash,
    latest_version,
    thread_id,
)
from app.integrations.gemini.bridge import get_gateway
from app.integrations.gemini.service import GeminiError
from app.integrations.media.gemini_media import GeminiMediaService, MediaGenerationError, get_media_service
from app.integrations.meko.client import MekoClient, get_meko
from app.integrations.storage.local import LocalStorage, get_storage
from app.models import (
    AgentRun,
    Approval,
    Brand,
    Campaign,
    CampaignScenario,
    ContentItem,
    ContentVersion,
    GuardianReview,
)
from app.schemas.agents import MarketGapReport
from app.schemas.core import Request, Response
from app.security.context import TenantContext, require
from app.security.permissions import Permission
from app.services.brand_context import AgentLog, NoApprovedProfile, load_brand_context

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/organizations/{org_id}", tags=["content"])

Feedback = Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=2000)]


class ContentCreate(Request):
    scenario_id: uuid.UUID
    kind: Literal["organic", "ad"] = "organic"


class HumanEdit(Request):
    hook: Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=500)]
    script: Annotated[str, StringConstraints(strip_whitespace=True, min_length=10, max_length=8000)]
    caption: Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=2200)]
    cta: Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=300)]
    hashtags: list[str] = Field(default_factory=list, max_length=15)


class Revise(Request):
    feedback: Feedback


class Decision(Request):
    approve: bool
    feedback: Feedback | None = None


class VersionOut(Response):
    version: int
    source: str
    hook: str
    script: str
    caption: str
    cta: str
    hashtags: list[str]
    scene_plan: list[dict]
    research: dict
    content_hash: str
    created_at: datetime


class ReviewOut(Response):
    id: uuid.UUID
    content_version: int
    status: str
    findings: list[dict]
    model: str
    created_at: datetime


class ApprovalOut(Response):
    id: uuid.UUID
    content_version: int
    decision: str
    feedback: str | None
    created_at: datetime
    decided_at: datetime | None


class ContentOut(Response):
    id: uuid.UUID
    brand_id: uuid.UUID
    campaign_id: uuid.UUID
    title: str
    platform: str
    kind: str
    status: str
    current_version: int
    created_at: datetime


class MediaOut(BaseModel):
    id: str
    scene_index: int | None
    content_type: str
    model: str
    created_at: str
    url: str


class MediaState(BaseModel):
    images: list[MediaOut]
    video: MediaOut | None


class ContentDetail(ContentOut):
    version: VersionOut | None
    versions: list[int]
    reviews: list[ReviewOut]
    approvals: list[ApprovalOut]
    media: MediaState


class GenerateImage(Request):
    scene_index: int = Field(ge=0, le=20)


class ContentList(BaseModel):
    items: list[ContentOut]


class ContentRow(ContentOut):
    brand_name: str


class ContentRows(BaseModel):
    items: list[ContentRow]


class GuardianRow(BaseModel):
    id: uuid.UUID
    content_id: uuid.UUID
    title: str
    brand_name: str
    content_version: int
    status: str
    findings: int
    created_at: datetime


class GuardianRows(BaseModel):
    items: list[GuardianRow]


class AgentRunRow(BaseModel):
    id: uuid.UUID
    graph_name: str
    status: str
    brand_name: str
    started_at: datetime


class AgentRunRows(BaseModel):
    items: list[AgentRunRow]


class PendingApproval(BaseModel):
    approval_id: uuid.UUID
    content: ContentOut
    brand_name: str
    content_version: int
    guardian_status: str | None
    created_at: datetime


class PendingList(BaseModel):
    items: list[PendingApproval]


def _item(db: Session, tenant: TenantContext, content_id: uuid.UUID) -> ContentItem:
    item = db.scalar(
        select(ContentItem).where(
            ContentItem.id == content_id, ContentItem.organization_id == tenant.organization_id
        )
    )
    if item is None:
        raise HTTPException(status_code=404, detail="content not found")
    return item


def _detail(db: Session, item: ContentItem, version_number: int | None = None) -> ContentDetail:
    scope = (ContentVersion.organization_id == item.organization_id, ContentVersion.content_id == item.id)
    numbers = list(db.scalars(select(ContentVersion.version).where(*scope).order_by(ContentVersion.version)))
    version = db.scalar(
        select(ContentVersion).where(
            *scope, ContentVersion.version == (version_number or item.current_version)
        )
    )
    reviews = db.scalars(
        select(GuardianReview)
        .where(GuardianReview.organization_id == item.organization_id, GuardianReview.content_id == item.id)
        .order_by(GuardianReview.created_at.desc())
    ).all()
    approvals = db.scalars(
        select(Approval)
        .where(Approval.organization_id == item.organization_id, Approval.content_id == item.id)
        .order_by(Approval.created_at.desc())
    ).all()
    return ContentDetail(
        **ContentOut.model_validate(item).model_dump(),
        version=VersionOut.model_validate(version) if version else None,
        versions=numbers,
        reviews=[ReviewOut.model_validate(row) for row in reviews],
        approvals=[ApprovalOut.model_validate(row) for row in approvals],
        media=_media_state(item),
    )


def _media_state(item: ContentItem) -> MediaState:
    """Only the current version's media is shown. Older versions keep theirs, in case you switch back."""
    media = item.media or {}
    key = str(item.current_version)

    def out(entry: dict, scene_index: int | None) -> MediaOut:
        return MediaOut(
            id=entry["id"],
            scene_index=scene_index,
            content_type=entry["content_type"],
            model=entry["model"],
            created_at=entry["created_at"],
            url=f"/organizations/{item.organization_id}/content/{item.id}/media/{entry['id']}",
        )

    images = (media.get("images") or {}).get(key, {})
    video = (media.get("video") or {}).get(key)
    return MediaState(
        images=[out(entry, int(scene)) for scene, entry in sorted(images.items(), key=lambda kv: int(kv[0]))],
        video=out(video, None) if video else None,
    )


def _supersede_pending(db: Session, item: ContentItem) -> None:
    """A new version voids any approval still waiting on an older one."""
    db.execute(
        update(Approval)
        .where(
            Approval.organization_id == item.organization_id,
            Approval.content_id == item.id,
            Approval.decision == "pending",
        )
        .values(decision="superseded", decided_at=datetime.now(UTC))
    )


def _run_graph(
    db: Session,
    model: Model,
    meko: MekoClient | None,
    tenant: TenantContext,
    item: ContentItem,
    *,
    write_draft: bool,
    feedback: str | None = None,
) -> None:
    enforce_ai_limit(db, tenant.organization_id)
    run = start_run(
        db, tenant, item.brand_id, "content_production", model.model, campaign_id=item.campaign_id
    )
    next_version = item.current_version + 1 if write_draft else item.current_version
    try:
        with checkpointer() as saver:
            graph = build_content_graph(db, model, meko, saver, item=item, user_id=tenant.user.id)
            graph.invoke(
                {"write_draft": write_draft, "feedback": feedback},
                {"configurable": {"thread_id": thread_id(item.id, next_version)}},
            )
    except (GeminiError, NoApprovedProfile) as exc:
        log.warning("content workflow failed: %s", exc)
        db.rollback()
        item.status = "failed"
        finish_run(db, run, error=type(exc).__name__)
        status = 409 if isinstance(exc, NoApprovedProfile) else 502
        detail = (
            "approve a brand profile first"
            if isinstance(exc, NoApprovedProfile)
            else "AI could not finish this content. Try again."
        )
        raise HTTPException(status_code=status, detail=detail) from exc
    finish_run(db, run, detail={"content_id": str(item.id), "version": item.current_version})


@router.post("/brands/{brand_id}/content", response_model=ContentDetail, status_code=201)
def create_content(
    brand_id: uuid.UUID,
    body: ContentCreate,
    tenant: TenantContext = Depends(require(Permission.CAMPAIGN_EDIT)),
    db: Session = Depends(get_db),
    model: Model = Depends(get_gateway),
    meko: MekoClient | None = Depends(get_meko),
) -> ContentDetail:
    get_brand_or_404(db, tenant, brand_id)
    row = db.execute(
        select(CampaignScenario, Campaign)
        .join(
            Campaign,
            (Campaign.id == CampaignScenario.campaign_id)
            & (Campaign.organization_id == CampaignScenario.organization_id),
        )
        .where(
            CampaignScenario.id == body.scenario_id,
            CampaignScenario.organization_id == tenant.organization_id,
            Campaign.brand_id == brand_id,
        )
    ).first()
    if row is None:
        raise HTTPException(status_code=404, detail="idea not found")
    scenario, campaign = row
    item = ContentItem(
        organization_id=tenant.organization_id,
        brand_id=brand_id,
        campaign_id=campaign.id,
        scenario_id=scenario.id,
        title=scenario.title,
        platform=scenario.platform,
        kind=body.kind,
        created_by=tenant.user.id,
    )
    db.add(item)
    db.commit()
    _run_graph(db, model, meko, tenant, item, write_draft=True)
    return _detail(db, item)


@router.get("/brands/{brand_id}/content", response_model=ContentList)
def list_content(
    brand_id: uuid.UUID,
    tenant: TenantContext = Depends(require(Permission.CAMPAIGN_VIEW)),
    db: Session = Depends(get_db),
) -> ContentList:
    get_brand_or_404(db, tenant, brand_id)
    rows = db.scalars(
        select(ContentItem)
        .where(ContentItem.organization_id == tenant.organization_id, ContentItem.brand_id == brand_id)
        .order_by(ContentItem.created_at.desc())
        .limit(100)
    )
    return ContentList(items=[ContentOut.model_validate(row) for row in rows])


@router.get("/content", response_model=ContentRows)
def list_all_content(
    tenant: TenantContext = Depends(require(Permission.CAMPAIGN_VIEW)),
    db: Session = Depends(get_db),
) -> ContentRows:
    rows = db.execute(
        select(ContentItem, Brand.name)
        .join(
            Brand,
            (Brand.id == ContentItem.brand_id) & (Brand.organization_id == ContentItem.organization_id),
        )
        .where(ContentItem.organization_id == tenant.organization_id)
        .order_by(ContentItem.created_at.desc())
        .limit(100)
    ).all()
    return ContentRows(
        items=[
            ContentRow(**ContentOut.model_validate(item).model_dump(), brand_name=name) for item, name in rows
        ]
    )


@router.get("/agent-runs", response_model=AgentRunRows)
def list_agent_runs(
    tenant: TenantContext = Depends(require(Permission.CAMPAIGN_VIEW)),
    db: Session = Depends(get_db),
) -> AgentRunRows:
    rows = db.execute(
        select(AgentRun, Brand.name)
        .join(Brand, (Brand.id == AgentRun.brand_id) & (Brand.organization_id == AgentRun.organization_id))
        .where(AgentRun.organization_id == tenant.organization_id)
        .order_by(AgentRun.started_at.desc())
        .limit(50)
    ).all()
    return AgentRunRows(
        items=[
            AgentRunRow(
                id=run.id,
                graph_name=run.graph_name,
                status=run.status,
                brand_name=name,
                started_at=run.started_at,
            )
            for run, name in rows
        ]
    )


@router.get("/guardian-reviews", response_model=GuardianRows)
def list_guardian_reviews(
    tenant: TenantContext = Depends(require(Permission.CAMPAIGN_VIEW)),
    db: Session = Depends(get_db),
) -> GuardianRows:
    rows = db.execute(
        select(GuardianReview, ContentItem.title, Brand.name)
        .join(
            ContentItem,
            (ContentItem.id == GuardianReview.content_id)
            & (ContentItem.organization_id == GuardianReview.organization_id),
        )
        .join(
            Brand,
            (Brand.id == ContentItem.brand_id) & (Brand.organization_id == ContentItem.organization_id),
        )
        .where(GuardianReview.organization_id == tenant.organization_id)
        .order_by(GuardianReview.created_at.desc())
        .limit(100)
    ).all()
    return GuardianRows(
        items=[
            GuardianRow(
                id=review.id,
                content_id=review.content_id,
                title=title,
                brand_name=name,
                content_version=review.content_version,
                status=review.status,
                findings=len(review.findings),
                created_at=review.created_at,
            )
            for review, title, name in rows
        ]
    )


@router.get("/content/{content_id}", response_model=ContentDetail)
def get_content(
    content_id: uuid.UUID,
    version: int | None = None,
    tenant: TenantContext = Depends(require(Permission.CAMPAIGN_VIEW)),
    db: Session = Depends(get_db),
) -> ContentDetail:
    return _detail(db, _item(db, tenant, content_id), version)


@router.post("/content/{content_id}/revise", response_model=ContentDetail)
def revise_content(
    content_id: uuid.UUID,
    body: Revise,
    tenant: TenantContext = Depends(require(Permission.CAMPAIGN_EDIT)),
    db: Session = Depends(get_db),
    model: Model = Depends(get_gateway),
    meko: MekoClient | None = Depends(get_meko),
) -> ContentDetail:
    item = _item(db, tenant, content_id)
    if (item.publication or {}).get("published_at"):
        raise HTTPException(status_code=409, detail="published content cannot be changed")
    item.publication = None
    _supersede_pending(db, item)
    item.status = "generating"
    db.commit()
    _run_graph(db, model, meko, tenant, item, write_draft=True, feedback=body.feedback)
    return _detail(db, item)


@router.post("/content/{content_id}/edit", response_model=ContentDetail)
def edit_content(
    content_id: uuid.UUID,
    body: HumanEdit,
    tenant: TenantContext = Depends(require(Permission.CAMPAIGN_EDIT)),
    db: Session = Depends(get_db),
    model: Model = Depends(get_gateway),
    meko: MekoClient | None = Depends(get_meko),
) -> ContentDetail:
    """A person's edit makes a new version, which goes back through Guardian and needs new approval."""
    item = _item(db, tenant, content_id)
    if (item.publication or {}).get("published_at"):
        raise HTTPException(status_code=409, detail="published content cannot be changed")
    item.publication = None
    previous = latest_version(db, item)
    if previous is None:
        raise HTTPException(status_code=409, detail="this content has no version to edit yet")
    _supersede_pending(db, item)
    add_version(
        db,
        item,
        {**body.model_dump(), "scene_plan": previous.scene_plan, "research": previous.research},
        source="human",
        user_id=tenant.user.id,
    )
    item.status = "generating"
    db.commit()
    _run_graph(db, model, meko, tenant, item, write_draft=False)
    return _detail(db, item)


@router.post("/content/{content_id}/approvals/{approval_id}/decision", response_model=ContentDetail)
def decide(
    content_id: uuid.UUID,
    approval_id: uuid.UUID,
    body: Decision,
    tenant: TenantContext = Depends(require(Permission.CONTENT_APPROVE)),
    db: Session = Depends(get_db),
    model: Model = Depends(get_gateway),
    meko: MekoClient | None = Depends(get_meko),
) -> ContentDetail:
    item = _item(db, tenant, content_id)
    approval = db.scalar(
        select(Approval).where(
            Approval.id == approval_id,
            Approval.organization_id == tenant.organization_id,
            Approval.content_id == item.id,
        )
    )
    if approval is None:
        raise HTTPException(status_code=404, detail="approval not found")
    if approval.decision != "pending":
        raise HTTPException(status_code=409, detail="this approval has already been decided")
    if not body.approve and not body.feedback:
        raise HTTPException(status_code=422, detail="say what needs to change")
    version = latest_version(db, item)
    # Everything is checked again here: the exact version, its fingerprint and the Guardian verdict.
    if version is None or approval.content_version != version.version:
        raise HTTPException(status_code=409, detail="this approval is for an older version")
    fields = {
        "hook": version.hook,
        "script": version.script,
        "caption": version.caption,
        "cta": version.cta,
        "hashtags": version.hashtags,
        "scene_plan": version.scene_plan,
    }
    if content_hash(fields) != approval.content_hash or version.content_hash != approval.content_hash:
        raise HTTPException(status_code=409, detail="the content changed after review")
    review = db.scalar(
        select(GuardianReview)
        .where(
            GuardianReview.organization_id == tenant.organization_id,
            GuardianReview.content_id == item.id,
            GuardianReview.content_version == version.version,
        )
        .order_by(GuardianReview.created_at.desc())
    )
    if review is None or review.status == "BLOCKED":
        raise HTTPException(status_code=409, detail="Brand Guardian has not cleared this version")

    decision = "approved" if body.approve else "changes_requested"
    approval.decision = decision
    approval.feedback = body.feedback
    approval.reviewed_by = tenant.user.id
    approval.decided_at = datetime.now(UTC)
    item.status = decision
    db.commit()
    with checkpointer() as saver:
        graph = build_content_graph(db, model, meko, saver, item=item, user_id=tenant.user.id)
        graph.invoke(
            Command(resume=decision),
            {"configurable": {"thread_id": thread_id(item.id, version.version)}},
        )
    return _detail(db, item)


@router.get("/approvals", response_model=PendingList)
def pending_approvals(
    tenant: TenantContext = Depends(require(Permission.CAMPAIGN_VIEW)),
    db: Session = Depends(get_db),
) -> PendingList:
    rows = db.execute(
        select(Approval, ContentItem, Brand.name)
        .join(
            ContentItem,
            (ContentItem.id == Approval.content_id)
            & (ContentItem.organization_id == Approval.organization_id),
        )
        .join(
            Brand,
            (Brand.id == ContentItem.brand_id) & (Brand.organization_id == ContentItem.organization_id),
        )
        .where(Approval.organization_id == tenant.organization_id, Approval.decision == "pending")
        .order_by(Approval.created_at)
        .limit(100)
    ).all()
    items = []
    for approval, item, brand_name in rows:
        status = db.scalar(
            select(GuardianReview.status)
            .where(
                GuardianReview.organization_id == tenant.organization_id,
                GuardianReview.content_id == item.id,
                GuardianReview.content_version == approval.content_version,
            )
            .order_by(GuardianReview.created_at.desc())
        )
        items.append(
            PendingApproval(
                approval_id=approval.id,
                content=ContentOut.model_validate(item),
                brand_name=brand_name,
                content_version=approval.content_version,
                guardian_status=status,
                created_at=approval.created_at,
            )
        )
    return PendingList(items=items)


@router.post("/brands/{brand_id}/market-gaps", response_model=MarketGapReport)
def market_gaps(
    brand_id: uuid.UUID,
    tenant: TenantContext = Depends(require(Permission.CAMPAIGN_EDIT)),
    db: Session = Depends(get_db),
    model: Model = Depends(get_gateway),
    meko: MekoClient | None = Depends(get_meko),
) -> MarketGapReport:
    """Hypotheses to test, not findings. Nothing is saved until a person acts on one."""
    get_brand_or_404(db, tenant, brand_id)
    enforce_ai_limit(db, tenant.organization_id)
    try:
        context = load_brand_context(
            db, meko, tenant.organization_id, brand_id, "topics audience content gaps"
        )
    except NoApprovedProfile as exc:
        raise HTTPException(status_code=409, detail="approve a brand profile first") from exc
    topics = list(
        db.scalars(
            select(ContentItem.title)
            .where(ContentItem.organization_id == tenant.organization_id, ContentItem.brand_id == brand_id)
            .limit(30)
        )
    )
    run = start_run(db, tenant, brand_id, "market_gap", model.model)
    try:
        report = market_gap_agent(model, brand=context.data, recent_topics=topics)
    except GeminiError as exc:
        log.warning("market gap run failed: %s", exc)
        finish_run(db, run, error=type(exc).__name__)
        raise HTTPException(status_code=502, detail="AI could not finish this. Try again.") from exc
    finish_run(db, run, detail={"gaps": len(report.gaps)})
    AgentLog(meko, context.datapack_id, f"Market gaps: {brand_id}").record(
        "Market Gap", "suggest topics to test", report.model_dump_json()
    )
    return report


def _video_aspect_ratio(platform: str) -> str:
    return (
        "9:16" if platform.lower() in {"instagram", "tiktok", "reel", "reels", "story", "shorts"} else "16:9"
    )


def _require_unpublished_version(db: Session, item: ContentItem) -> ContentVersion:
    if (item.publication or {}).get("published_at"):
        raise HTTPException(status_code=409, detail="published content cannot be changed")
    version = latest_version(db, item)
    if version is None:
        raise HTTPException(status_code=409, detail="this content has no version to generate media for yet")
    return version


@router.post("/content/{content_id}/media/image", response_model=ContentDetail)
def generate_scene_image(
    content_id: uuid.UUID,
    body: GenerateImage,
    tenant: TenantContext = Depends(require(Permission.CAMPAIGN_EDIT)),
    db: Session = Depends(get_db),
    media: GeminiMediaService = Depends(get_media_service),
    storage: LocalStorage = Depends(get_storage),
    meko: MekoClient | None = Depends(get_meko),
) -> ContentDetail:
    item = _item(db, tenant, content_id)
    version = _require_unpublished_version(db, item)
    if body.scene_index >= len(version.scene_plan):
        raise HTTPException(status_code=404, detail="scene not found")
    scene = version.scene_plan[body.scene_index]
    enforce_ai_limit(db, tenant.organization_id)
    run = start_run(
        db, tenant, item.brand_id, "image_generation", media.image_model, campaign_id=item.campaign_id
    )
    prompt = (
        f"{scene['visual_description']}. On-screen text, if any: {scene.get('on_screen_text') or 'none'}. "
        f"Style: clean, photoreal, suited to a {item.platform} post. "
        "No real people, no logos, no on-image text."
    )
    try:
        result = media.generate_image(prompt)
    except MediaGenerationError as exc:
        log.warning("image generation failed: %s", exc)
        finish_run(db, run, error=type(exc).__name__)
        raise HTTPException(status_code=502, detail="Could not generate an image. Try again.") from exc
    media_id = uuid.uuid4()
    ext = ".jpg" if "jpeg" in result.content_type else ".png"
    storage.save_content_media(tenant.organization_id, item.id, media_id, ext, result.data)
    entry = {
        "id": str(media_id),
        "content_type": result.content_type,
        "model": media.image_model,
        "created_at": datetime.now(UTC).isoformat(),
    }
    current = item.media or {}
    images = dict(current.get("images") or {})
    for_version = dict(images.get(str(item.current_version)) or {})
    for_version[str(body.scene_index)] = entry
    images[str(item.current_version)] = for_version
    item.media = {**current, "images": images}
    db.commit()
    finish_run(db, run, detail={"scene_index": body.scene_index})
    brand = get_brand_or_404(db, tenant, item.brand_id)
    datapack_id = (meko.shared_datapack_id or brand.meko_datapack_id) if meko else None
    AgentLog(meko, datapack_id, f"Content workflow: {item.title} ({item.id})").record(
        "Image", f"generate the image for scene {body.scene_index}", prompt
    )
    return _detail(db, item)


@router.post("/content/{content_id}/media/video", response_model=ContentDetail)
def generate_video(
    content_id: uuid.UUID,
    tenant: TenantContext = Depends(require(Permission.CAMPAIGN_EDIT)),
    db: Session = Depends(get_db),
    media: GeminiMediaService = Depends(get_media_service),
    storage: LocalStorage = Depends(get_storage),
    meko: MekoClient | None = Depends(get_meko),
) -> ContentDetail:
    item = _item(db, tenant, content_id)
    version = _require_unpublished_version(db, item)
    enforce_ai_limit(db, tenant.organization_id)
    run = start_run(
        db, tenant, item.brand_id, "video_generation", media.video_model, campaign_id=item.campaign_id
    )
    scenes = "; ".join(
        f"scene {i + 1}: {scene['visual_description']}" for i, scene in enumerate(version.scene_plan)
    )
    prompt = (
        f"Hook: {version.hook}. {scenes or version.script[:300]}. "
        f"Style: clean, photoreal, suited to a {item.platform} post. "
        "No real people, no logos, no text overlays."
    )
    try:
        result = media.generate_video(prompt, aspect_ratio=_video_aspect_ratio(item.platform))
    except MediaGenerationError as exc:
        log.warning("video generation failed: %s", exc)
        finish_run(db, run, error=type(exc).__name__)
        raise HTTPException(status_code=502, detail="Could not generate a video. Try again.") from exc
    media_id = uuid.uuid4()
    storage.save_content_media(tenant.organization_id, item.id, media_id, ".mp4", result.data)
    entry = {
        "id": str(media_id),
        "content_type": result.content_type,
        "model": media.video_model,
        "created_at": datetime.now(UTC).isoformat(),
    }
    current = item.media or {}
    videos = dict(current.get("video") or {})
    videos[str(item.current_version)] = entry
    item.media = {**current, "video": videos}
    db.commit()
    finish_run(db, run, detail={})
    brand = get_brand_or_404(db, tenant, item.brand_id)
    datapack_id = (meko.shared_datapack_id or brand.meko_datapack_id) if meko else None
    AgentLog(meko, datapack_id, f"Content workflow: {item.title} ({item.id})").record(
        "Video", "generate a video for this content", prompt
    )
    return _detail(db, item)


@router.get("/content/{content_id}/media/{media_id}")
def get_media_file(
    content_id: uuid.UUID,
    media_id: uuid.UUID,
    tenant: TenantContext = Depends(require(Permission.CAMPAIGN_VIEW)),
    db: Session = Depends(get_db),
    storage: LocalStorage = Depends(get_storage),
) -> RawResponse:
    """Serves the bytes directly. media_id must appear in this content's own media record, not guessed."""
    item = _item(db, tenant, content_id)
    media = item.media or {}
    found = next(
        (
            entry
            for group in (media.get("images") or {}).values()
            for entry in group.values()
            if entry["id"] == str(media_id)
        ),
        None,
    ) or next(
        (entry for entry in (media.get("video") or {}).values() if entry["id"] == str(media_id)),
        None,
    )
    if found is None:
        raise HTTPException(status_code=404, detail="media not found")
    ext = (
        ".mp4"
        if found["content_type"] == "video/mp4"
        else (".jpg" if "jpeg" in found["content_type"] else ".png")
    )
    key = f"organizations/{tenant.organization_id}/content/{item.id}/media/{media_id}{ext}"
    try:
        data = storage.read(key)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="media file is missing") from exc
    return RawResponse(content=data, media_type=found["content_type"])
