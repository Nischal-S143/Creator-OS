"""The full learning loop on the real cluster with a fake model, including attempts to skip approval."""

import pytest

from app.integrations.gemini.bridge import get_gateway
from app.integrations.gemini.service import GeminiUnavailableError
from app.integrations.meko.client import get_meko
from app.main import app
from app.schemas.agents import FeedbackHypothesis, FeedbackReportDraft
from app.schemas.ai import CampaignIdeasDraft
from tests.test_content_flow import FakeModel, api, create_content, ready_brand


class Model(FakeModel):
    feedback_down = False

    def generate_json(self, prompt, schema, *, system=None):
        if schema is FeedbackReportDraft:
            self.calls.append(schema.__name__)
            self.prompts.append((prompt, system or ""))
            if self.feedback_down:
                raise GeminiUnavailableError("down")
            return FeedbackReportDraft(
                summary="Views were above this brand's usual level.",
                hypotheses=[
                    FeedbackHypothesis(
                        observation="Views were higher than the median",
                        hypothesis="Short hooks may hold attention better for this brand",
                        suggested_experiment="Test a short hook against a long hook",
                        confidence="medium",
                    )
                ],
            )
        return super().generate_json(prompt, schema, system=system)


@pytest.fixture
def model(client):
    fake = Model()
    app.dependency_overrides[get_gateway] = lambda: fake
    app.dependency_overrides[get_meko] = lambda: None
    return fake


def approved_content(client, headers, org, base, idea):
    content = create_content(client, headers, base, idea)
    path = api(f"/organizations/{org}/content/{content['id']}")
    decided = client.post(
        f"{path}/approvals/{content['approvals'][0]['id']}/decision", json={"approve": True}, headers=headers
    )
    assert decided.status_code == 200, decided.text
    return content, path


def publish(client, headers, path):
    r = client.post(f"{path}/published", json={"url": "https://example.com/post/1"}, headers=headers)
    assert r.status_code == 200, r.text
    return r.json()


def test_unapproved_content_cannot_be_scheduled_or_published(client, make_user, model):
    headers, org, base, idea = ready_brand(client, make_user)
    content = create_content(client, headers, base, idea)
    path = api(f"/organizations/{org}/content/{content['id']}")
    assert (
        client.post(
            f"{path}/schedule", json={"scheduled_for": "2030-01-01T10:00:00Z"}, headers=headers
        ).status_code
        == 409
    )
    assert (
        client.post(f"{path}/published", json={"url": "https://example.com/p"}, headers=headers).status_code
        == 409
    )
    assert (
        client.post(f"{path}/results", json={"window": "48h", "views": 1}, headers=headers).status_code == 409
    )


def test_editing_approved_content_removes_the_right_to_publish(client, make_user, model):
    headers, org, base, idea = ready_brand(client, make_user)
    _, path = approved_content(client, headers, org, base, idea)
    edited = client.post(
        f"{path}/edit",
        json={
            "hook": "New hook",
            "script": "A changed script here.",
            "caption": "Cap",
            "cta": "Go",
            "hashtags": [],
        },
        headers=headers,
    )
    assert edited.status_code == 200, edited.text
    assert (
        client.post(f"{path}/published", json={"url": "https://example.com/p"}, headers=headers).status_code
        == 409
    )


def test_learning_loop_from_results_to_the_next_campaign(client, make_user, model):
    headers, org, base, idea = ready_brand(client, make_user)
    content, path = approved_content(client, headers, org, base, idea)

    scheduled = client.post(
        f"{path}/schedule", json={"scheduled_for": "2030-01-01T10:00:00Z"}, headers=headers
    )
    assert scheduled.status_code == 200 and scheduled.json()["scheduled_for"].startswith("2030-01-01")
    published = publish(client, headers, path)
    assert published["url"] == "https://example.com/post/1"
    rows = client.get(api(f"/organizations/{org}/calendar"), headers=headers).json()["items"]
    assert [row["content_id"] for row in rows] == [content["id"]]

    no_numbers = client.post(f"{path}/results", json={"window": "48h"}, headers=headers)
    assert no_numbers.status_code == 422
    report = client.post(f"{path}/results", json={"window": "48h", "views": 500, "saves": 9}, headers=headers)
    assert report.status_code == 200, report.text
    body = report.json()
    assert body["comparison"]["verdict"] == "insufficient_data"
    assert body["comparison"]["metrics"]["views"]["value"] == 500
    assert body["summary"] and body["hypotheses"]
    prompt = model.prompts[-1]
    assert '"views"' in prompt[0] and "add none of your own" in prompt[1]

    lessons = client.get(api(f"{base}/lessons"), headers=headers).json()["items"]
    assert len(lessons) == 1 and lessons[0]["status"] == "proposed"
    assert lessons[0]["confidence"] == "low", "thin evidence cannot claim more than low confidence"

    campaign = client.post(
        api(f"{base}/campaigns"), json={"name": "Next", "objective": "Grow again"}, headers=headers
    ).json()["id"]
    client.post(api(f"{base}/campaigns/{campaign}/generate"), headers=headers)
    assert "Short hooks may hold" not in model.prompts[-1][0], "unapproved lessons never reach agents"

    decision = api(f"{base}/lessons/{lessons[0]['id']}/decision")
    approved = client.post(decision, json={"approve": True}, headers=headers)
    assert approved.status_code == 200, approved.text
    assert approved.json()["items"][0]["status"] == "approved" and approved.json()["items"][0]["review_at"]
    assert client.post(decision, json={"approve": False}, headers=headers).status_code == 409

    client.post(api(f"{base}/campaigns/{campaign}/generate"), headers=headers)
    prompt = next(p for p, s in reversed(model.prompts) if "Propose exactly three" in s)
    assert "Short hooks may hold" in prompt, "approved lessons shape the next campaign"
    assert CampaignIdeasDraft.__name__ in model.calls


def test_rejected_lesson_never_reaches_campaigns(client, make_user, model):
    headers, org, base, idea = ready_brand(client, make_user)
    _, path = approved_content(client, headers, org, base, idea)
    publish(client, headers, path)
    client.post(f"{path}/results", json={"window": "48h", "views": 5}, headers=headers)
    lesson = client.get(api(f"{base}/lessons"), headers=headers).json()["items"][0]
    client.post(api(f"{base}/lessons/{lesson['id']}/decision"), json={"approve": False}, headers=headers)
    campaign = client.post(
        api(f"{base}/campaigns"), json={"name": "Next", "objective": "Grow again"}, headers=headers
    ).json()["id"]
    client.post(api(f"{base}/campaigns/{campaign}/generate"), headers=headers)
    assert "Short hooks may hold" not in model.prompts[-1][0]


def test_measured_report_survives_an_ai_outage(client, make_user, model):
    headers, org, base, idea = ready_brand(client, make_user)
    _, path = approved_content(client, headers, org, base, idea)
    publish(client, headers, path)
    model.feedback_down = True
    report = client.post(f"{path}/results", json={"window": "7d", "views": 50}, headers=headers)
    assert report.status_code == 200, report.text
    assert (
        report.json()["ai_available"] is False
        and report.json()["comparison"]["metrics"]["views"]["value"] == 50
    )
    assert client.get(api(f"{base}/lessons"), headers=headers).json()["items"] == []


def test_other_tenants_and_read_only_roles_are_refused(client, make_user, model):
    owner, org, base, idea = ready_brand(client, make_user)
    _, path = approved_content(client, owner, org, base, idea)
    publish(client, owner, path)
    client.post(f"{path}/results", json={"window": "48h", "views": 5}, headers=owner)
    lesson = client.get(api(f"{base}/lessons"), headers=owner).json()["items"][0]
    other, other_org, other_base, _ = ready_brand(client, make_user)
    assert client.get(f"{path}/results", headers=other).status_code == 404
    assert client.get(api(f"{base}/lessons"), headers=other).status_code == 404
    forged = path.replace(org, other_org)
    assert (
        client.post(f"{forged}/published", json={"url": "https://e.com/x"}, headers=other).status_code == 404
    )
    assert client.get(api(f"/organizations/{other_org}/calendar"), headers=other).json()["items"] == []
    analyst = make_user()
    email = client.get(api("/me"), headers=analyst).json()["email"]
    client.post(api(f"/organizations/{org}/members"), json={"email": email, "role": "analyst"}, headers=owner)
    decision = api(f"{base}/lessons/{lesson['id']}/decision")
    assert client.post(decision, json={"approve": True}, headers=analyst).status_code == 403
    assert (
        client.post(f"{path}/results", json={"window": "7d", "views": 1}, headers=analyst).status_code == 403
    )


def test_campaign_report_shows_the_whole_story_and_lessons_used(client, make_user, model):
    headers, org, base, idea = ready_brand(client, make_user)
    content, path = approved_content(client, headers, org, base, idea)
    publish(client, headers, path)
    client.post(f"{path}/results", json={"window": "48h", "views": 5}, headers=headers)
    first_campaign = content["campaign_id"]

    report = client.get(api(f"{base}/campaigns/{first_campaign}/report"), headers=headers)
    assert report.status_code == 200, report.text
    body = report.json()
    assert [item["id"] for item in body["content"]] == [content["id"]]
    assert body["content"][0]["guardian_status"] == "PASS"
    assert body["content"][0]["url"] == "https://example.com/post/1"
    assert body["content"][0]["reviews"][0]["metrics"]["views"]["value"] == 5
    assert body["lessons_learned"][0]["status"] == "proposed"
    assert body["lessons_used"] == []

    lesson = body["lessons_learned"][0]
    client.post(api(f"{base}/lessons/{lesson['id']}/decision"), json={"approve": True}, headers=headers)
    campaign = client.post(
        api(f"{base}/campaigns"), json={"name": "Next", "objective": "Grow again"}, headers=headers
    ).json()["id"]
    generated = client.post(api(f"{base}/campaigns/{campaign}/generate"), headers=headers).json()
    assert generated["runs"][0]["detail"]["lessons_used"][0]["lesson"] == lesson["text"]
    next_report = client.get(api(f"{base}/campaigns/{campaign}/report"), headers=headers).json()
    assert next_report["lessons_used"][0]["source"] == content["title"]
    assert next_report["content"] == [] and next_report["lessons_learned"] == []

    other, other_org, other_base, _ = ready_brand(client, make_user)
    assert client.get(api(f"{base}/campaigns/{campaign}/report"), headers=other).status_code == 404
    forged = other_base + f"/campaigns/{campaign}/report"
    assert client.get(api(forged), headers=other).status_code == 404
