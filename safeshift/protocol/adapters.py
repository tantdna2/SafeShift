"""Offline adapter skeletons, explicit response envelopes and coordinate units.

No SDK dependency, HTTP client, credential lookup or paid-call implementation.
Envelope fixtures are handcrafted contracts, not live API compatibility evidence.
"""

from dataclasses import dataclass, replace
from pathlib import Path

from . import ADAPTER_VERSION
from .firewall import external_path
from .prompts import COORDINATE_INSTRUCTION, Request
from .schema import strict_json


@dataclass(frozen=True)
class ProviderAdapter:
    provider: str
    convention: str
    api_key_env: str
    endpoint_env: str
    version: str = ADAPTER_VERSION

    def prepare(self, repo: Path, request: Request) -> Request:
        external_path(repo, request.image_path)
        if request.task == "classification" or self.convention == "xyxy_1":
            return request
        order = "[ymin, xmin, ymax, xmax]" if self.convention == "yxyx_1000" else "[xmin, ymin, xmax, ymax]"
        prompt = request.prompt.replace("[xmin, ymin, xmax, ymax]", order)
        instruction = COORDINATE_INSTRUCTION.replace("[xmin, ymin, xmax, ymax]", order)
        prompt = prompt.replace(instruction, f"Use {order} coordinates in [0,1000], origin at the top left.")
        return replace(request, prompt=prompt)

    def send(self, request: Request):
        raise RuntimeError("OFFLINE_ONLY: provider transport disabled before freeze")

    def extract_text(self, response: bytes) -> str:
        obj = strict_json(response)
        if not isinstance(obj, dict) or obj.get("error"):
            raise ValueError("provider response error or invalid envelope")
        try:
            if self.provider == "gemini":
                candidates = obj["candidates"]
                if len(candidates) != 1 or candidates[0].get("finishReason") != "STOP":
                    raise ValueError("expected one complete Gemini candidate")
                parts = candidates[0]["content"]["parts"]
                if len(parts) != 1 or parts[0].get("thought") or not isinstance(parts[0].get("text"), str):
                    raise ValueError("expected one non-thinking text part")
                text = parts[0]["text"]
            elif self.provider == "qwen_dashscope":
                # Explicit OpenAI-compatible chat envelope; native DashScope is not guessed.
                choices = obj["choices"]
                if len(choices) != 1 or choices[0].get("finish_reason") != "stop":
                    raise ValueError("expected one complete DashScope compatible choice")
                message = choices[0]["message"]
                if message.get("refusal") or message.get("tool_calls"):
                    raise ValueError("refusal/tool call is not a task response")
                text = message["content"]
            elif self.provider == "openai":
                if obj.get("status") != "completed":
                    raise ValueError("OpenAI response is incomplete")
                messages = [item for item in obj["output"] if item.get("type") != "reasoning"]
                if len(messages) != 1 or messages[0].get("type") != "message":
                    raise ValueError("expected one OpenAI output message")
                blocks = messages[0]["content"]
                if len(blocks) != 1 or blocks[0].get("type") != "output_text":
                    raise ValueError("refusal or non-text OpenAI output")
                text = blocks[0]["text"]
            elif self.provider == "anthropic":
                if obj.get("stop_reason") != "end_turn":
                    raise ValueError("Anthropic response is incomplete")
                blocks = [item for item in obj["content"] if item.get("type") not in ("thinking", "redacted_thinking")]
                if len(blocks) != 1 or blocks[0].get("type") != "text":
                    raise ValueError("expected one Anthropic text block")
                text = blocks[0]["text"]
            else:
                raise ValueError("unknown provider")
        except (KeyError, IndexError, TypeError, AttributeError) as exc:
            raise ValueError("malformed provider envelope") from exc
        if not isinstance(text, str):
            raise ValueError("provider content must be text")
        return text


ADAPTERS = {
    "gemini": ProviderAdapter("gemini", "yxyx_1000", "GEMINI_API_KEY", "GEMINI_ENDPOINT"),
    "qwen_dashscope": ProviderAdapter("qwen_dashscope", "xyxy_1000", "DASHSCOPE_API_KEY", "QWEN_WORKSPACE_ENDPOINT"),
    "openai": ProviderAdapter("openai", "xyxy_1", "OPENAI_API_KEY", "OPENAI_ENDPOINT"),
    "anthropic": ProviderAdapter("anthropic", "xyxy_1", "ANTHROPIC_API_KEY", "ANTHROPIC_ENDPOINT"),
}
