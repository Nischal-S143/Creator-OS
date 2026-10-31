"""Scores and clean-up done by code, so the model never supplies the final numbers."""

import re

from app.schemas.agents import AudienceCluster, StrategyDraft

CRITERIA_WEIGHTS = {
    "brand_fit": 25,
    "audience_relevance": 25,
    "feasibility": 15,
    "differentiation": 15,
    "risk_safety": 10,
    "evidence_quality": 10,
}
MAX_COMMENTS = 300
MAX_COMMENT_CHARS = 500
_URL_ONLY = re.compile(r"^(https?://\S+\s*)+$", re.IGNORECASE)


def score_strategy(strategy: StrategyDraft) -> int:
    """A weighted total out of 100. The weights are fixed here and shown to people."""
    total = sum(
        getattr(strategy.ratings, name).score / 5 * weight for name, weight in CRITERIA_WEIGHTS.items()
    )
    return round(total)


def clean_comments(raw: str) -> tuple[list[str], int]:
    """One comment per line, without blanks, link-only lines or exact duplicates. Returns kept and removed."""
    kept: list[str] = []
    seen: set[str] = set()
    removed = 0
    for line in raw.splitlines():
        comment = line.strip()
        if not comment:
            continue
        key = re.sub(r"\s+", " ", comment).casefold()
        if key in seen or _URL_ONLY.match(comment) or not re.search(r"\w", comment):
            removed += 1
            continue
        seen.add(key)
        kept.append(comment[:MAX_COMMENT_CHARS])
    return kept[:MAX_COMMENTS], removed + max(0, len(kept) - MAX_COMMENTS)


def score_clusters(clusters: list[AudienceCluster], comment_count: int) -> list[dict]:
    """Counts come from the comments each cluster actually claims, not from anything the model states."""
    scored = []
    used: set[int] = set()
    for cluster in clusters:
        numbers = sorted({n for n in cluster.comment_numbers if 1 <= n <= comment_count} - used)
        used.update(numbers)
        if not numbers:
            continue
        share = len(numbers) / comment_count
        score = round(share * 50 + cluster.brand_relevance / 5 * 30 + (20 if cluster.content_gap else 0))
        scored.append(
            {
                **cluster.model_dump(exclude={"comment_numbers"}),
                "comment_count": len(numbers),
                "opportunity_score": score,
            }
        )
    return sorted(scored, key=lambda item: item["opportunity_score"], reverse=True)
