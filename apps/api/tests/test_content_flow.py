"""Content workflow on the real cluster with a fake model, including attempts to bypass approval."""

import uuid

import pytest
from sqlalchemy import delete, select, update
from sqlalchemy.exc import DBAPIError

from app.db.session import set_rls
from app.integrations.gemini.bridge import get_gateway
from app.integrations.meko.client import get_meko
from app.main import app
from app.models import Approval, ContentVersion
from app.schemas.agents import (
    GuardianFinding,
    GuardianResult,
    MarketGap,
    MarketGapReport,
    ResearchBrief,
    Scene,
    ScenePlan,
    ScriptDraft,
)
from app.schemas.ai import BrandProfileDraft, CampaignIdeaDraft, CampaignIdeasDraft
from tests.helpers import unique


class FakeModel:
    model = "fake-model"

    def __init__(self):
        self.findings: list[GuardianFinding] = []
        self.calls: list[str] = []
        self.prompts: list[tuple[str, str]] = []

    def generate_json(self, prompt, schema, *, system=None):
        self.calls.append(schema.__name__)
        self.prompts.append((prompt, system or ""))
        if schema is BrandProfileDraft:
            return BrandProfileDraft(
                voice="Plain",
                tone="Warm",
                audience="Parents",
                content_pillars=["Workouts"],
                restrictions=["No health claims"],
            )
        if schema is CampaignIdeasDraft:
            return CampaignIdeasDraft(
                ideas=[
                    CampaignIdeaDraft(
                        title=f"Idea {n}",
                        hook="A hook line",
                        description="A long enough description",
                        platform="instagram",
                        content_format="reel",
                    )
                    for n in range(3)
                ]
            )
        if schema is ResearchBrief:
            return ResearchBrief(
                audience_questions=["How long?"],
                competitor_themes=[],
                angles=["Short sessions"],
                claims_to_verify=[],
                limitations=["No web access"],
            )
        if schema is ScriptDraft:
            return ScriptDraft(
                hook="Short on time?",
                script=f"Draft number {self.calls.count('ScriptDraft')} of the script.",
                caption="A caption",
                cta="Try it",
                hashtags=["#move"],
            )
        if schema is ScenePlan:
            return ScenePlan(
                scenes=[
                    Scene(
                        purpose="Hook",
                        visual_description="Someone tying shoes",
                        on_screen_text="Short on time?",
                        duration_seconds=3,
                    )
                ]
            )
        if schema is GuardianResult:
            return GuardianResult(findings=self.findings)
        if schema is MarketGapReport:
            return MarketGapReport(
                gaps=[
                    MarketGap(
                        topic="Topic",
                        why_it_may_be_open="A possible reason",
                        evidence_to_collect=["Audience survey"],
                        confidence="low",
                    )
                ],
                limitations=["No market data"],
            )
        raise AssertionError(schema)


BLOCKER = GuardianFinding(
    check_type="restrictions", severity="blocker", evidence="cures", recommendation="Remove it"
)
WARNING = GuardianFinding(check_type="claims", severity="warning", evidence="best", recommendation="Check it")


@pytest.fixture
def model(client):
    fake = FakeModel()
    app.dependency_overrides[get_gateway] = lambda: fake
    app.dependency_overrides[get_meko] = lambda: None
    return fake


def api(path):
    return f"/api/v1{path}"


def ready_brand(client, make_user):
    """Owner with an approved profile and a generated idea. Returns everything a test needs."""
    headers = make_user()
    org = client.post(
        api("/organizations"), json={"name": "A", "slug": unique("org")}, headers=headers
    ).json()["id"]
    brand = client.post(
        api(f"/organizations/{org}/brands"), json={"name": "B", "slug": unique("b")}, headers=headers
    ).json()["id"]
    base = f"/organizations/{org}/brands/{brand}"
    document = client.post(
        api(f"{base}/documents"), files={"file": ("g.txt", b"Plain warm voice.")}, headers=headers
    ).json()["id"]
    profile = client.post(api(f"{base}/documents/{document}/extract-profile"), headers=headers).json()["id"]
    client.post(api(f"{base}/profiles/{profile}/decision"), json={"approve": True}, headers=headers)
    campaign = client.post(
        api(f"{base}/campaigns"), json={"name": "C", "objective": "Grow"}, headers=headers
    ).json()["id"]
    ideas = client.post(api(f"{base}/campaigns/{campaign}/generate"), headers=headers).json()["scenarios"]
    return headers, org, base, ideas[0]["id"]


def create_content(client, headers, base, idea, kind="organic"):
    r = client.post(api(f"{base}/content"), json={"scenario_id": idea, "kind": kind}, headers=headers)
    assert r.status_code == 201, r.text
    return r.json()


def test_agents_run_in_order_and_stop_at_human_approval(client, make_user, model):
    headers, org, base, idea = ready_brand(client, make_user)
    model.calls.clear()
    content = create_content(client, headers, base, idea)
    assert model.calls == ["ResearchBrief", "ScriptDraft", "ScenePlan", "GuardianResult"]
    assert content["status"] == "in_review" and content["current_version"] == 1
    assert content["version"]["source"] == "agent" and content["version"]["scene_plan"]
    assert content["reviews"][0]["status"] == "PASS"
    assert content["approvals"][0]["decision"] == "pending"

    pending = client.get(api(f"/organizations/{org}/approvals"), headers=headers).json()["items"]
    assert [p["content"]["id"] for p in pending] == [content["id"]]

    decided = client.post(
        api(
            f"/organizations/{org}/content/{content['id']}/approvals/{content['approvals'][0]['id']}/decision"
        ),
        json={"approve": True},
        headers=headers,
    )
    assert decided.status_code == 200, decided.text
    assert decided.json()["status"] == "approved"
    assert client.get(api(f"/organizations/{org}/approvals"), headers=headers).json()["items"] == []


def test_guardian_verdict_comes_from_findings_not_the_model(client, make_user, model):
    headers, org, base, idea = ready_brand(client, make_user)
    model.findings = [WARNING]
    assert create_content(client, headers, base, idea)["reviews"][0]["status"] == "NEEDS_REVIEW"
    model.findings = [WARNING, BLOCKER]
    blocked = create_content(client, headers, base, idea)
    assert blocked["reviews"][0]["status"] == "BLOCKED" and blocked["status"] == "blocked"
    assert blocked["approvals"] == [], "blocked content never reaches a person for approval"


def test_guardian_never_sees_the_writers_research(client, make_user, model):
    headers, _, base, idea = ready_brand(client, make_user)
    create_content(client, headers, base, idea)
    index = len(model.calls) - 1 - model.calls[::-1].index("GuardianResult")
    guardian_prompt = model.prompts[index][0]
    assert "No web access" not in guardian_prompt and "Short sessions" not in guardian_prompt


def test_edit_makes_a_new_version_and_voids_the_old_approval(client, make_user, model):
    headers, org, base, idea = ready_brand(client, make_user)
    content = create_content(client, headers, base, idea)
    old_approval = content["approvals"][0]["id"]
    path = api(f"/organizations/{org}/content/{content['id']}")
    edited = client.post(
        f"{path}/edit",
        json={
            "hook": "New hook",
            "script": "A person rewrote this script.",
            "caption": "New caption",
            "cta": "Go",
            "hashtags": [],
        },
        headers=headers,
    )
    assert edited.status_code == 200, edited.text
    body = edited.json()
    assert body["current_version"] == 2 and body["version"]["source"] == "human"
    assert body["versions"] == [1, 2]
    assert body["version"]["content_hash"] != content["version"]["content_hash"]
    statuses = {a["id"]: a["decision"] for a in body["approvals"]}
    assert statuses[old_approval] == "superseded"
    stale = client.post(f"{path}/approvals/{old_approval}/decision", json={"approve": True}, headers=headers)
    assert stale.status_code == 409, "an approval for an old version cannot be used"
    first = client.get(f"{path}?version=1", headers=headers).json()
    assert first["version"]["hook"] == "Short on time?", "old versions are kept as written"


def test_changes_requested_then_ai_revision(client, make_user, model):
    headers, org, base, idea = ready_brand(client, make_user)
    content = create_content(client, headers, base, idea)
    path = api(f"/organizations/{org}/content/{content['id']}")
    approval = content["approvals"][0]["id"]
    no_reason = client.post(f"{path}/approvals/{approval}/decision", json={"approve": False}, headers=headers)
    assert no_reason.status_code == 422
    decided = client.post(
        f"{path}/approvals/{approval}/decision",
        json={"approve": False, "feedback": "Make it shorter"},
        headers=headers,
    )
    assert decided.json()["status"] == "changes_requested"
    revised = client.post(f"{path}/revise", json={"feedback": "Make it shorter"}, headers=headers)
    assert revised.status_code == 200, revised.text
    assert revised.json()["current_version"] == 2 and revised.json()["status"] == "in_review"
    script_prompt = model.prompts[len(model.calls) - 1 - model.calls[::-1].index("ScriptDraft")][0]
    assert "Make it shorter" in script_prompt


def test_an_approval_cannot_be_decided_twice(client, make_user, model):
    headers, org, base, idea = ready_brand(client, make_user)
    content = create_content(client, headers, base, idea)
    path = api(
        f"/organizations/{org}/content/{content['id']}/approvals/{content['approvals'][0]['id']}/decision"
    )
    assert client.post(path, json={"approve": True}, headers=headers).status_code == 200
    assert client.post(path, json={"approve": False, "feedback": "no"}, headers=headers).status_code == 409


def test_database_refuses_changes_to_history(client, make_user, model, db):
    headers, org, base, idea = ready_brand(client, make_user)
    content = create_content(client, headers, base, idea)
    org_id, content_id = uuid.UUID(org), uuid.UUID(content["id"])
    path = api(
        f"/organizations/{org}/content/{content['id']}/approvals/{content['approvals'][0]['id']}/decision"
    )
    client.post(path, json={"approve": True}, headers=headers)
    set_rls(db, tenant_id=org_id)
    scope = ContentVersion.content_id == content_id
    assert db.execute(update(ContentVersion).where(scope).values(script="tampered")).rowcount == 0
    assert db.execute(delete(ContentVersion).where(scope)).rowcount == 0
    done = Approval.content_id == content_id
    assert db.execute(update(Approval).where(done).values(decision="pending")).rowcount == 0
    assert db.execute(delete(Approval).where(done)).rowcount == 0
    db.rollback()
    assert db.scalar(select(ContentVersion.script).where(scope)).startswith("Draft number")


def test_cross_tenant_content_cannot_be_inserted(client, make_user, model, db):
    headers_a, org_a, base_a, idea = ready_brand(client, make_user)
    content = create_content(client, headers_a, base_a, idea)
    _, org_b, _, _ = ready_brand(client, make_user)
    set_rls(db, tenant_id=uuid.UUID(org_b))
    db.add(
        Approval(
            organization_id=uuid.UUID(org_a),
            content_id=uuid.UUID(content["id"]),
            content_version=1,
            content_hash="x",
            decision="approved",
        )
    )
    with pytest.raises(DBAPIError):
        db.commit()
    db.rollback()


def test_other_tenants_get_404(client, make_user, model):
    headers_a, org_a, base_a, idea = ready_brand(client, make_user)
    content = create_content(client, headers_a, base_a, idea)
    headers_b, org_b, base_b, idea_b = ready_brand(client, make_user)
    approval = content["approvals"][0]["id"]
    for method, path, kwargs in [
        ("get", f"/organizations/{org_b}/content/{content['id']}", {}),
        ("get", f"/organizations/{org_a}/content/{content['id']}", {}),
        ("post", f"/organizations/{org_b}/content/{content['id']}/revise", {"json": {"feedback": "hack it"}}),
        (
            "post",
            f"/organizations/{org_b}/content/{content['id']}/approvals/{approval}/decision",
            {"json": {"approve": True}},
        ),
        ("post", f"{base_b}/content", {"json": {"scenario_id": idea}}),
    ]:
        assert getattr(client, method)(api(path), headers=headers_b, **kwargs).status_code == 404, path
    assert client.get(api(f"/organizations/{org_b}/approvals"), headers=headers_b).json()["items"] == []


def test_only_approvers_can_decide(client, make_user, model):
    owner, org, base, idea = ready_brand(client, make_user)
    content = create_content(client, owner, base, idea)
    path = api(
        f"/organizations/{org}/content/{content['id']}/approvals/{content['approvals'][0]['id']}/decision"
    )
    for role in ("editor", "analyst", "client_approver"):
        person = make_user()
        email = client.get(api("/me"), headers=person).json()["email"]
        client.post(api(f"/organizations/{org}/members"), json={"email": email, "role": role}, headers=owner)
        assert client.post(path, json={"approve": True}, headers=person).status_code == 403, role


def test_each_agent_step_is_logged_to_the_brands_memory_conversation(client, make_user, model):
    from tests.test_milestone import FakeMeko

    meko = FakeMeko()
    app.dependency_overrides[get_meko] = lambda: meko
    headers, _, base, idea = ready_brand(client, make_user)
    meko.turns.clear()
    create_content(client, headers, base, idea)
    assert [agent for _, agent in meko.turns] == ["Research", "Script", "Visual", "Brand Guardian"]
    assert len({pack for pack, _ in meko.turns}) == 1


def test_shared_datapack_setting_is_refused_outside_development(monkeypatch):
    from app.core.config import get_settings

    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("MEKO_SHARED_DATAPACK_ID", "00000000-0000-0000-0000-000000000001")
    monkeypatch.setenv("MEKO_API_KEY", "x")
    get_settings.cache_clear()
    get_meko.cache_clear()
    try:
        with pytest.raises(RuntimeError):
            get_meko()
    finally:
        monkeypatch.undo()
        get_settings.cache_clear()
        get_meko.cache_clear()


def test_ad_content_uses_the_same_review_and_approval(client, make_user, model):
    headers, _, base, idea = ready_brand(client, make_user)
    ad = create_content(client, headers, base, idea, kind="ad")
    assert ad["kind"] == "ad" and ad["approvals"][0]["decision"] == "pending"


def test_market_gaps_are_hypotheses_and_need_a_profile(client, make_user, model):
    headers, _, base, _ = ready_brand(client, make_user)
    report = client.post(api(f"{base}/market-gaps"), headers=headers).json()
    assert report["gaps"][0]["confidence"] in {"low", "medium"} and report["limitations"]
