"""Meko MCP adapter.

Behaviour checked against the live server (Meko MCP 3.2.4) on 31 October 2026:
- An API key can reach every datapack on the account, so `datapack_id` is the only boundary between brands.
- Tool failures can arrive as a normal result holding an "error" field.
- `datapack_create` needs a conversation id, although its schema does not mark it required.
"""

import json
import threading
from functools import lru_cache
from typing import Any

import httpx

from app.core.config import get_settings

AGENT_ID = "creatoros"
ALLOWED_TOOLS = frozenset(
    {
        "conversation_add_message",
        "conversation_create",
        "datapack_create",
        "memory_add",
        "memory_search",
    }
)


class MekoError(Exception):
    """A Meko call failed. Messages never contain the API key."""


class MekoClient:
    def __init__(self, url: str, api_key: str, timeout: float = 90, shared_datapack_id: str | None = None):
        self._url = url
        # Development only: one datapack for all brands, separated by a brand tag on each memory.
        self.shared_datapack_id = shared_datapack_id
        self._headers = {
            "Authorization": f"Bearer {api_key}",
            "User-Agent": "meko-mcp-installer/1.0",
            "Accept": "application/json, text/event-stream",
            "Content-Type": "application/json",
        }
        self._http = httpx.Client(timeout=timeout)
        self._session_id: str | None = None
        self._next_id = 1
        self._lock = threading.Lock()

    @staticmethod
    def _parse(response: httpx.Response) -> dict:
        if "text/event-stream" in response.headers.get("content-type", ""):
            for line in response.text.splitlines():
                if line.startswith("data:"):
                    return json.loads(line[5:])
            raise ValueError("empty event stream")
        return response.json()

    def _post(self, body: dict) -> httpx.Response:
        headers = dict(self._headers)
        if self._session_id:
            headers["Mcp-Session-Id"] = self._session_id
        return self._http.post(self._url, headers=headers, json=body)

    def _rpc_id(self) -> int:
        self._next_id += 1
        return self._next_id

    def _initialize(self) -> None:
        self._session_id = None
        response = self._post(
            {
                "jsonrpc": "2.0",
                "id": self._rpc_id(),
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-03-26",
                    "capabilities": {},
                    "clientInfo": {"name": "creatoros", "version": "0.1"},
                },
            }
        )
        if response.status_code != 200:
            raise MekoError(f"initialize failed with status {response.status_code}")
        self._session_id = response.headers.get("mcp-session-id")
        self._post({"jsonrpc": "2.0", "method": "notifications/initialized"})

    def _send(self, tool: str, arguments: dict[str, Any]) -> Any:
        body = {
            "jsonrpc": "2.0",
            "id": self._rpc_id(),
            "method": "tools/call",
            "params": {"name": tool, "arguments": arguments},
        }
        try:
            with self._lock:
                if self._session_id is None:
                    self._initialize()
                response = self._post(body)
                if response.status_code in (400, 404):  # The server dropped the session.
                    self._initialize()
                    response = self._post(body)
            if response.status_code != 200:
                raise MekoError(f"{tool} failed with status {response.status_code}")
            payload = self._parse(response)
        except (httpx.HTTPError, ValueError) as exc:
            raise MekoError(f"{tool} failed: {type(exc).__name__}") from exc
        if "error" in payload:
            raise MekoError(f"{tool} failed: {payload['error'].get('message', 'unknown')}")
        result = payload["result"]
        data = result.get("structuredContent")
        if data is None:
            data = "".join(part.get("text", "") for part in result.get("content", []))
        if isinstance(data, dict) and isinstance(data.get("result"), str):
            data = data["result"]
        if isinstance(data, str):
            try:
                data = json.loads(data)
            except ValueError:
                pass
        if result.get("isError") or (isinstance(data, dict) and "error" in data):
            code = data.get("error") if isinstance(data, dict) else "tool_error"
            raise MekoError(f"{tool} failed: {code}")
        return data

    def _call(self, tool: str, **arguments: Any) -> Any:
        if tool not in ALLOWED_TOOLS:
            raise MekoError(f"tool not allowed: {tool}")
        if tool != "datapack_create":  # Datapack management tools do not accept agent_id.
            arguments["agent_id"] = AGENT_ID
        return self._send(tool, arguments)

    def _conversation(self, datapack_id: str | None, title: str) -> str:
        arguments = {"title": title}
        if datapack_id:
            arguments["datapack_id"] = datapack_id
        return self._call("conversation_create", **arguments)["id"]

    def create_datapack(self, name: str) -> str:
        conversation_id = self._conversation(None, "creatoros datapack setup")
        return self._call("datapack_create", name=name, conversation_id=conversation_id)["datapack_id"]

    def add_memory(self, datapack_id: str, text: str, metadata: dict[str, str]) -> None:
        if not datapack_id:
            raise MekoError("datapack_id is required")
        conversation_id = self._conversation(datapack_id, "brand memory")
        self._call(
            "memory_add",
            text=text,
            metadata=json.dumps(metadata),  # The tool accepts metadata only as a JSON string.
            datapack_id=datapack_id,
            conversation_id=conversation_id,
        )

    def search_memory(
        self, datapack_id: str, query: str, limit: int = 8, brand_id: str | None = None
    ) -> list[str]:
        if not datapack_id:
            raise MekoError("datapack_id is required")
        conversation_id = self._conversation(datapack_id, "brand context")
        found = self._call(
            "memory_search",
            query=query,
            limit=limit * 4 if self.shared_datapack_id else limit,
            datapack_id=datapack_id,
            conversation_id=conversation_id,
        )
        results = found.get("results", [])
        if self.shared_datapack_id:
            # A shared datapack does not separate brands, so a memory must carry this brand's tag.
            results = [
                item
                for item in results
                if brand_id and (item.get("metadata") or {}).get("brand_id") == brand_id
            ][:limit]
        return [item["memory"] for item in results if item.get("memory")]

    def start_conversation(self, datapack_id: str, title: str) -> str:
        if not datapack_id:
            raise MekoError("datapack_id is required")
        return self._conversation(datapack_id, title)

    def log_agent_turn(
        self, datapack_id: str, conversation_id: str, *, agent: str, task: str, output: str
    ) -> None:
        """Records one agent step for traceability.

        Meko extracts memories from the input side of a turn, so input holds only the agent's name and
        task. Unapproved or untrusted text must never go there, or it could become brand memory.
        """
        if not datapack_id:
            raise MekoError("datapack_id is required")
        self._call(
            "conversation_add_message",
            conversation_id=conversation_id,
            datapack_id=datapack_id,
            input=f"{agent} agent: {task}",
            output=output[:8000],
        )


@lru_cache
def get_meko() -> MekoClient | None:
    settings = get_settings()
    if not settings.meko_api_key:
        return None
    if settings.meko_shared_datapack_id and settings.app_env != "development":
        raise RuntimeError("MEKO_SHARED_DATAPACK_ID is for development only")
    return MekoClient(
        settings.meko_mcp_url,
        settings.meko_api_key.get_secret_value(),
        shared_datapack_id=settings.meko_shared_datapack_id,
    )
