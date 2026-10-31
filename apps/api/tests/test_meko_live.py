"""Real Meko service. Creates throwaway datapacks and always deletes them."""

import json
import time

import pytest

from app.core.config import get_settings
from app.integrations.meko.client import MekoClient, MekoError
from tests.helpers import unique


@pytest.fixture
def meko():
    settings = get_settings()
    if not settings.meko_api_key:
        pytest.skip("MEKO_API_KEY is not set")
    return MekoClient(settings.meko_mcp_url, settings.meko_api_key.get_secret_value())


@pytest.fixture
def datapacks(meko):
    created: list[str] = []

    def create() -> str:
        try:
            pack = meko.create_datapack(unique("creatoros-test"))
        except MekoError as exc:
            if "FREE_TIER_DATAPACK_LIMIT" in str(exc):
                pytest.skip("the Meko plan cannot create more datapacks, so this was not tested")
            raise
        created.append(pack)
        return pack

    yield create
    setup = meko._conversation(None, "creatoros test cleanup")
    for pack in created:
        meko._send("datapack_delete", {"datapack_id": pack, "conversation_id": setup})


def test_two_brand_leakage(meko, datapacks):
    pack_a, pack_b = datapacks(), datapacks()
    codeword = unique("zebra")
    meko.add_memory(pack_a, f"The brand codeword is {codeword}.", {"source": "test"})
    query = f"What is the brand codeword {codeword}?"
    assert any(codeword in memory for memory in meko.search_memory(pack_a, query))
    assert not any(codeword in memory for memory in meko.search_memory(pack_b, query))


@pytest.mark.parametrize("method", ["add", "search"])
def test_missing_datapack_is_refused_locally(meko, method):
    with pytest.raises(MekoError):
        if method == "add":
            meko.add_memory("", "text", {})
        else:
            meko.search_memory("", "query")


@pytest.mark.parametrize("tool", ["memory_delete_all", "datapack_delete", "amp_cluster_delete"])
def test_unlisted_tools_are_refused(meko, tool):
    with pytest.raises(MekoError):
        meko._call(tool, conversation_id="x")


def test_errors_never_include_the_key():
    secret = "mko_tkn_should_not_appear"  # noqa: S105
    client = MekoClient("https://mcp.mekodata.ai/mcp", secret, timeout=30)
    with pytest.raises(MekoError) as exc:
        client.search_memory("00000000-0000-0000-0000-000000000000", "query")
    assert secret not in str(exc.value)


def test_shared_datapack_keeps_brands_apart_by_tag():
    """The development default datapack holds every brand, so filtering by tag is what separates them."""
    settings = get_settings()
    if not settings.meko_api_key or not settings.meko_shared_datapack_id:
        pytest.skip("shared datapack is not configured")
    meko = MekoClient(
        settings.meko_mcp_url,
        settings.meko_api_key.get_secret_value(),
        shared_datapack_id=settings.meko_shared_datapack_id,
    )
    pack = settings.meko_shared_datapack_id
    codeword = unique("zebra")
    meko.add_memory(pack, f"The brand codeword is {codeword}.", {"brand_id": "brand-a"})
    query = f"What is the brand codeword {codeword}?"
    try:
        assert any(codeword in m for m in meko.search_memory(pack, query, brand_id="brand-a"))
        assert meko.search_memory(pack, query, brand_id="brand-b") == []
        assert meko.search_memory(pack, query) == [], "no brand means no shared memories"
    finally:
        setup = meko._conversation(pack, "creatoros test cleanup")
        found = meko._send(
            "memory_search",
            {"query": query, "datapack_id": pack, "conversation_id": setup, "agent_id": "creatoros"},
        )
        for item in found.get("results", []):
            if codeword in item.get("memory", ""):
                meko._send(
                    "memory_delete_by_id",
                    {"memory_id": item["id"], "conversation_id": setup, "agent_id": "creatoros"},
                )


def test_agent_turn_is_stored_and_its_input_side_holds_only_the_task(meko, datapacks):
    pack = datapacks()
    conversation = meko.start_conversation(pack, "agent log test")
    meko.log_agent_turn(pack, conversation, agent="Research", task="prepare a brief", output='{"ok": true}')
    # Meko writes turns in the background, so allow it a moment.
    count = 0
    for _ in range(10):
        stored = meko._send(
            "conversation_get",
            {"conversation_id": conversation, "datapack_id": pack, "agent_id": "creatoros"},
        )
        count = stored.get("message_count", 0)
        if count:
            break
        time.sleep(3)
    assert count == 1, json.dumps(stored)[:200]
