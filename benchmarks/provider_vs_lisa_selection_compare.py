import asyncio
import json
import sys
import urllib.request
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lisa.core.context import SessionContext, Capability
from lisa.core.kernel import LisaRuntime
from lisa.providers.base import BaseProvider, ChatRequest, ChatResponse
from lisa.providers.manifest import ProviderManifest
from lisa.telemetry.flight_recorder import FlightRecorder
from lisa.tools.filesystem.read_file import ReadFileTool


class DirectSelectionProvider(BaseProvider):
    @property
    def id(self) -> str:
        return "direct_selection_provider"

    @property
    def name(self) -> str:
        return "Direct Selection Provider"

    async def handshake(self) -> ProviderManifest:
        return ProviderManifest(
            id=self.id,
            name=self.name,
            version="1.0.0",
            healthy=True,
            supported_models=["qwen3:4b"],
            capabilities=[Capability.CHAT, Capability.TOOLS],
        )

    async def is_healthy(self) -> bool:
        return True

    async def chat(self, request: ChatRequest) -> ChatResponse:
        payload = {
            "model": "qwen3:4b",
            "messages": request.messages,
            "stream": False,
            "options": {"temperature": request.temperature},
        }
        req = urllib.request.Request(
            "http://localhost:11434/api/chat",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=300) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            msg = data.get("message", {})
            return ChatResponse(content=msg.get("content", ""), tool_calls=msg.get("tool_calls"), usage={})


async def run_direct_provider() -> dict:
    provider = DirectSelectionProvider()
    manifest = await provider.handshake()
    prompt = "Select the candidate with the strongest evidence. Return its ID only."
    candidates = {
        "candidates": [
            {"id": "A", "confidence": 0.90, "support": 5, "contradictions": 0},
            {"id": "B", "confidence": 0.40, "support": 2, "contradictions": 3},
        ]
    }
    full_prompt = f"{prompt}\n\nCandidate set:\n{json.dumps(candidates, sort_keys=True)}"
    request = ChatRequest(messages=[{"role": "user", "content": full_prompt}], model="qwen3:4b", temperature=0.7)
    response = await provider.chat(request)
    return {
        "mode": "direct_provider",
        "prompt": full_prompt,
        "candidate_payload": candidates,
        "response": response.content,
        "response_raw": response.__dict__,
        "provider_id": provider.id,
        "timestamp": datetime.now().isoformat(),
    }


async def run_lisa_path() -> dict:
    recorder = FlightRecorder(session_id="provider_vs_lisa_selection", log_dir=Path(__file__).resolve().parent)
    runtime = LisaRuntime(flight_recorder=recorder)
    await runtime.initialize()
    await runtime.register_provider(DirectSelectionProvider())
    runtime.tool_registry.register(ReadFileTool())

    ctx = SessionContext(
        project_path="/home/user/Projects/lisa",
        workspace_name="provider_vs_lisa_selection",
        provider_id="direct_selection_provider",
        model_name="qwen3:4b",
        capabilities=[Capability.CHAT, Capability.TOOLS],
    )
    session = runtime.create_session(ctx)
    prompt = "Select the candidate with the strongest evidence. Return its ID only."
    candidates = {
        "candidates": [
            {"id": "A", "confidence": 0.90, "support": 5, "contradictions": 0},
            {"id": "B", "confidence": 0.40, "support": 2, "contradictions": 3},
        ]
    }
    full_prompt = f"{prompt}\n\nCandidate set:\n{json.dumps(candidates, sort_keys=True)}"
    response = await session.send_message(full_prompt)
    await runtime.shutdown()
    return {
        "mode": "lisa_path",
        "prompt": full_prompt,
        "candidate_payload": candidates,
        "response": response,
        "events": recorder.get_events(),
        "timestamp": datetime.now().isoformat(),
    }


async def main() -> None:
    direct_result = await run_direct_provider()
    lisa_result = await run_lisa_path()
    artifact = {
        "experiment_id": "BLIND-E2E-011",
        "title": "Provider vs L.I.S.A. Selection A/B",
        "timestamp": datetime.now().isoformat(),
        "direct_provider": direct_result,
        "lisa_path": lisa_result,
    }
    out_path = Path(__file__).resolve().parent / f"provider_vs_lisa_selection_{datetime.now().strftime('%Y-%m-%d_%H%M%S')}.json"
    out_path.write_text(json.dumps(artifact, indent=2), encoding="utf-8")
    print(json.dumps(artifact, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
