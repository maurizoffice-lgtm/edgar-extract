"""Talking to a local LLM through Ollama (free, runs on this machine).

Every request is cached on disk: the same request (model + messages + tools + options)
is never sent twice. Start Ollama with `ollama serve` before running extractions.
"""

import hashlib
import json
import time
from dataclasses import dataclass
from pathlib import Path

import httpx

from edgar_extract.config import CACHE_DIR

OLLAMA_URL = "http://localhost:11434"
LLM_CACHE_DIR = CACHE_DIR / "llm"

# Ollama silently cuts off prompts longer than its context window, so set it explicitly.
CONTEXT_TOKENS = 16_384

# USD per 1M input / output tokens. Local models are free.
PRICES_PER_MTOK: dict[str, tuple[float, float]] = {
    "qwen3.5:4b": (0.0, 0.0),
    "qwen3.5:2b": (0.0, 0.0),
}


class LLMUnavailableError(RuntimeError):
    pass


@dataclass(frozen=True)
class LLMResponse:
    model: str
    tool_arguments: dict | None  # arguments of the first tool call, if any
    content: str  # plain text answer (usually empty when a tool was called)
    input_tokens: int
    output_tokens: int
    duration_s: float
    cost_usd: float
    cached: bool
    raw: dict


def cost_usd(model: str, input_tokens: int, output_tokens: int) -> float:
    price_in, price_out = PRICES_PER_MTOK.get(model, (0.0, 0.0))
    return (input_tokens * price_in + output_tokens * price_out) / 1_000_000


class OllamaClient:
    def __init__(
        self,
        base_url: str = OLLAMA_URL,
        cache_dir: Path = LLM_CACHE_DIR,
        http: httpx.Client | None = None,
    ):
        self.base_url = base_url
        self.cache_dir = Path(cache_dir)
        self.http = http or httpx.Client(timeout=600.0)

    def build_request(self, model: str, prompt: str, tools: list[dict]) -> dict:
        return {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "tools": tools,
            "stream": False,
            "think": False,  # the qwen3.5 models would otherwise "think" first: slower, not needed here
            "options": {"temperature": 0, "num_ctx": CONTEXT_TOKENS},
        }

    def _cache_path(self, body: dict) -> Path:
        key = hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()[:24]
        return self.cache_dir / body["model"].replace(":", "_") / f"{key}.json"

    def chat(self, model: str, prompt: str, tools: list[dict]) -> LLMResponse:
        body = self.build_request(model, prompt, tools)
        path = self._cache_path(body)
        cached = path.exists()

        if cached:
            raw = json.loads(path.read_text())
        else:
            started = time.monotonic()
            try:
                response = self.http.post(f"{self.base_url}/api/chat", json=body)
            except httpx.ConnectError:
                raise LLMUnavailableError("Ollama is not running. Start it with: ollama serve") from None
            response.raise_for_status()
            raw = response.json()
            raw["_duration_s"] = round(time.monotonic() - started, 2)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(raw, indent=1))

        message = raw.get("message", {})
        tool_calls = message.get("tool_calls") or []
        arguments = tool_calls[0]["function"].get("arguments") if tool_calls else None
        if isinstance(arguments, str):  # some models return the arguments as a JSON string
            try:
                arguments = json.loads(arguments)
            except json.JSONDecodeError:
                arguments = None

        input_tokens = raw.get("prompt_eval_count", 0)
        output_tokens = raw.get("eval_count", 0)
        return LLMResponse(
            model=model,
            tool_arguments=arguments,
            content=message.get("content", ""),
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            duration_s=raw.get("_duration_s", 0.0),
            cost_usd=cost_usd(model, input_tokens, output_tokens),
            cached=cached,
            raw=raw,
        )
