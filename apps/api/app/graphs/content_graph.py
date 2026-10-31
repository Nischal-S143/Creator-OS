"""Content workflow: research, script, scene plan, Guardian review, then a pause for human approval.

The approval pause is a LangGraph interrupt with a durable checkpoint. Resuming only records a decision
the API has already authorized, so the graph can never approve anything by itself.
"""

import hashlib
import json
import uuid
from typing import TypedDict

from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents import specialists
from app.integrations.meko.client import MekoClient
from app.models import (
    Approval,
    Campaign,
    CampaignScenario,
    ContentItem,
    ContentVersion,
    GuardianReview,
)
from app.schemas.agents import ResearchBrief, ScriptDraft
from app.services.brand_context import AgentLog, BrandContext, load_brand_context


class ContentState(TypedDict, total=False):
    # Identifiers and position only. Content lives in immutable YugabyteDB rows.
    write_draft: bool
    feedback: str | None
    research: dict
    draft: dict
    decision: str


def content_hash(version_fields: dict) -> str:
    """Fingerprint of exactly what a person approves."""
    canonical = json.dumps(
        {key: version_fields[key] for key in ("hook", "script", "caption", "cta", "hashtags", "scene_plan")},
        sort_keys=True,
        default=str,
    )
    return hashlib.sha256(canonical.encode()).hexdigest()


def thread_id(content_id: uuid.UUID, version: int) -> str:
    return f"content:{content_id}:v{version}"


def latest_version(db: Session, item: ContentItem) -> ContentVersion | None:
    return db.scalar(
        select(ContentVersion).where(
            ContentVersion.organization_id == item.organization_id,
            ContentVersion.content_id == item.id,
            ContentVersion.version == item.current_version,
        )
    )


def add_version(
    db: Session, item: ContentItem, fields: dict, *, source: str, user_id: uuid.UUID
) -> ContentVersion:
    item.current_version += 1
    version = ContentVersion(
        organization_id=item.organization_id,
        content_id=item.id,
        version=item.current_version,
        source=source,
        content_hash=content_hash(fields),
        created_by=user_id,
        **fields,
    )
    db.add(version)
    db.flush()
    return version


def build_content_graph(
    db: Session,
    model: specialists.Model,
    meko: MekoClient | None,
    saver: PostgresSaver,
    *,
    item: ContentItem,
    user_id: uuid.UUID,
):
    def _idea() -> dict:
        scenario = db.scalar(
            select(CampaignScenario).where(
                CampaignScenario.organization_id == item.organization_id,
                CampaignScenario.id == item.scenario_id,
            )
        )
        campaign = db.scalar(
            select(Campaign).where(
                Campaign.organization_id == item.organization_id, Campaign.id == item.campaign_id
            )
        )
        return {
            "title": scenario.title,
            "hook": scenario.hook,
            "description": scenario.description,
            "platform": scenario.platform,
            "format": scenario.content_format,
            "campaign_objective": campaign.objective,
        }

    cached_context: BrandContext | None = None
    agent_log: AgentLog | None = None

    def _context() -> BrandContext:
        nonlocal cached_context
        if cached_context is None:
            query = f"{item.title} brand voice restrictions lessons"
            cached_context = load_brand_context(db, meko, item.organization_id, item.brand_id, query)
        return cached_context

    def _brand() -> dict:
        return _context().data

    def _log(agent: str, task: str, output: str) -> None:
        # One conversation per workflow run, so the hand-offs between agents read in order.
        nonlocal agent_log
        if agent_log is None:
            agent_log = AgentLog(meko, _context().datapack_id, f"Content workflow: {item.title} ({item.id})")
        agent_log.record(agent, task, output)

    def research(state: ContentState) -> ContentState:
        previous = latest_version(db, item)
        if previous is not None:  # Revisions keep the original brief.
            return {"research": previous.research}
        brief: ResearchBrief = specialists.research_agent(model, idea=_idea(), brand=_brand())
        _log("Research", "prepare a brief for the Script agent", brief.model_dump_json())
        return {"research": brief.model_dump()}

    def script(state: ContentState) -> ContentState:
        previous = latest_version(db, item)
        if item.kind == "ad":
            draft: ScriptDraft = specialists.ad_agent(
                model, idea=_idea(), brand=_brand(), research=state["research"]
            )
        else:
            draft = specialists.script_agent(
                model,
                idea=_idea(),
                brand=_brand(),
                research=state["research"],
                previous=None
                if previous is None
                else {
                    "hook": previous.hook,
                    "script": previous.script,
                    "caption": previous.caption,
                    "cta": previous.cta,
                },
                feedback=state.get("feedback"),
            )
        _log("Script", "write a draft from the Research brief for the Visual agent", draft.model_dump_json())
        return {"draft": draft.model_dump()}

    def visual(state: ContentState) -> ContentState:
        plan = specialists.visual_agent(model, draft=state["draft"], brand=_brand())
        fields = {
            **state["draft"],
            "scene_plan": [scene.model_dump() for scene in plan.scenes],
            "research": state["research"],
        }
        add_version(db, item, fields, source="agent", user_id=user_id)
        db.commit()
        _log("Visual", "plan scenes from the Script draft for Brand Guardian", plan.model_dump_json())
        return {}

    def guardian(_state: ContentState) -> ContentState:
        version = latest_version(db, item)
        result = specialists.guardian_agent(
            model,
            content={
                "hook": version.hook,
                "script": version.script,
                "caption": version.caption,
                "cta": version.cta,
                "hashtags": version.hashtags,
                "scene_plan": version.scene_plan,
            },
            brand=_brand(),
            platform=item.platform,
        )
        status = specialists.guardian_status(result.findings)
        _log("Brand Guardian", f"independently review version {version.version}", result.model_dump_json())
        db.add(
            GuardianReview(
                organization_id=item.organization_id,
                content_id=item.id,
                content_version=version.version,
                status=status,
                findings=[finding.model_dump() for finding in result.findings],
                model=model.model,
            )
        )
        if status == "BLOCKED":
            item.status = "blocked"
        else:
            item.status = "in_review"
            db.add(
                Approval(
                    organization_id=item.organization_id,
                    content_id=item.id,
                    content_version=version.version,
                    content_hash=version.content_hash,
                )
            )
        db.commit()
        return {"decision": "blocked" if status == "BLOCKED" else "pending"}

    def await_approval(_state: ContentState) -> ContentState:
        return {"decision": interrupt({"content_id": str(item.id), "version": item.current_version})}

    graph = StateGraph(ContentState)
    graph.add_node("research", research)
    graph.add_node("script", script)
    graph.add_node("visual", visual)
    graph.add_node("guardian", guardian)
    graph.add_node("await_approval", await_approval)
    graph.add_conditional_edges(
        START, lambda state: "research" if state.get("write_draft") else "guardian", ["research", "guardian"]
    )
    graph.add_edge("research", "script")
    graph.add_edge("script", "visual")
    graph.add_edge("visual", "guardian")
    graph.add_conditional_edges(
        "guardian",
        lambda state: END if state["decision"] == "blocked" else "await_approval",
        ["await_approval", END],
    )
    graph.add_edge("await_approval", END)
    return graph.compile(checkpointer=saver)
