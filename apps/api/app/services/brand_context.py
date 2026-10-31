import logging
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.integrations.meko.client import MekoClient, MekoError
from app.models import Brand, BrandProfile

log = logging.getLogger(__name__)


class NoApprovedProfile(Exception):
    pass


@dataclass(frozen=True)
class BrandContext:
    data: dict
    memories: list[str]
    memory_used: bool
    datapack_id: str | None


def _approved_lessons(brand: Brand) -> list[dict]:
    today = datetime.now(UTC).isoformat()
    return [
        {"lesson": entry["text"], "source": entry["source_title"], "based_on_posts": entry["sample_size"]}
        for entry in brand.lessons or []
        if entry["status"] == "approved" and entry.get("review_at", "") > today
    ]


def load_brand_context(
    db: Session, meko: MekoClient | None, organization_id: uuid.UUID, brand_id: uuid.UUID, query: str
) -> BrandContext:
    """Approved profile from YugabyteDB, plus memory from this brand's own datapack.

    The datapack id comes only from this brand's row. If Meko is down the run continues, because the
    approved profile is authoritative.
    """
    profile = db.scalar(
        select(BrandProfile).where(
            BrandProfile.organization_id == organization_id,
            BrandProfile.brand_id == brand_id,
            BrandProfile.status == "approved",
        )
    )
    if profile is None:
        raise NoApprovedProfile
    brand = db.scalar(select(Brand).where(Brand.organization_id == organization_id, Brand.id == brand_id))
    memories: list[str] = []
    memory_used = False
    datapack_id = (meko.shared_datapack_id or brand.meko_datapack_id) if meko else None
    if meko and datapack_id:
        try:
            memories = meko.search_memory(datapack_id, query, brand_id=str(brand_id))
            memory_used = True
        except MekoError as exc:
            log.warning("meko context unavailable: %s", exc)
    return BrandContext(
        data={
            "name": brand.name,
            "voice": profile.voice,
            "tone": profile.tone,
            "audience": profile.audience,
            "content_pillars": profile.content_pillars,
            "restrictions": profile.restrictions,
            "memories": memories,
            "approved_lessons": _approved_lessons(brand),
        },
        memories=memories,
        memory_used=memory_used,
        datapack_id=datapack_id,
    )


class AgentLog:
    """Writes each agent step to the brand's Meko conversation. Failures never stop the workflow."""

    def __init__(self, meko: MekoClient | None, datapack_id: str | None, title: str):
        self._meko = meko
        self._datapack_id = datapack_id
        self._title = title
        self._conversation_id: str | None = None

    def record(self, agent: str, task: str, output: str) -> None:
        if not self._meko or not self._datapack_id:
            return
        try:
            if self._conversation_id is None:
                self._conversation_id = self._meko.start_conversation(self._datapack_id, self._title)
            self._meko.log_agent_turn(
                self._datapack_id, self._conversation_id, agent=agent, task=task, output=output
            )
        except MekoError as exc:
            log.warning("meko agent log failed: %s", exc)
