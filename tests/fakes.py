"""Test doubles for the LLM and an SSE parser, so the AI pipeline is testable
without a running Ollama."""
from __future__ import annotations

import json

from backend.services.llm_client import LLMUnavailable

SAMPLE_CONTRACT = """SERVICE AGREEMENT

1. Termination. Either party may terminate this Agreement upon thirty (30) days written notice to the other party.

2. Confidentiality. The parties shall keep all Confidential Information confidential for a period of three (3) years.

3. Payment. Client shall pay all fees within thirty (30) days of the invoice date.

4. Governing Law. This Agreement shall be governed by the laws of the State of New York.
"""

# Quotes below are verbatim substrings of SAMPLE_CONTRACT so verification passes.
_EXTRACTION = {
    "clauses": [
        {"key": "termination", "status": "found",
         "quote": "Either party may terminate this Agreement upon thirty (30) days written notice to the other party.",
         "explanation": "Either side can end the contract by giving 30 days' notice."},
        {"key": "confidentiality", "status": "found",
         "quote": "The parties shall keep all Confidential Information confidential for a period of three (3) years.",
         "explanation": "Both sides must keep information secret for three years."},
        {"key": "payment", "status": "found",
         "quote": "Client shall pay all fees within thirty (30) days of the invoice date.",
         "explanation": "The client pays within 30 days of being invoiced."},
        {"key": "governing_law", "status": "found",
         "quote": "This Agreement shall be governed by the laws of the State of New York.",
         "explanation": "New York state law governs the contract."},
    ]
}

_HEALTH = {
    "overall_score": 78,
    "dimensions": [
        {"key": "clarity", "score": 80, "explanation": "Clauses are clearly worded.",
         "quote": "This Agreement shall be governed by the laws of the State of New York."},
        {"key": "risk_exposure", "score": 70, "explanation": "No liability cap is present.", "quote": ""},
        {"key": "completeness", "score": 75, "explanation": "Most core clauses are present.", "quote": ""},
        {"key": "enforceability", "score": 85, "explanation": "Governing law is specified.",
         "quote": "This Agreement shall be governed by the laws of the State of New York."},
    ],
}

_CHAT_TOKENS = [
    "Based on the contract, ",
    '"Either party may terminate this Agreement upon thirty (30) days written notice to the other party."',
    " So you can end it with 30 days' notice.",
]


class FakeLLM:
    """Returns canned, grounded responses keyed off the prompt schema."""

    def __init__(self, extraction=None, health=None, stream_tokens=None):
        self.extraction = extraction if extraction is not None else _EXTRACTION
        self.health = health if health is not None else _HEALTH
        self.stream_tokens = stream_tokens if stream_tokens is not None else _CHAT_TOKENS

    async def complete(self, messages, *, json_mode=False, max_tokens=None, temperature=None):
        content = " ".join(m["content"] for m in messages)
        if '"dimensions"' in content:
            return json.dumps(self.health)
        return json.dumps(self.extraction)

    async def stream(self, messages, *, max_tokens=None, temperature=None):
        for token in self.stream_tokens:
            yield token

    async def ping(self):
        return True


class FailingLLM:
    """Simulates an unreachable LLM for degraded-path tests."""

    async def complete(self, *args, **kwargs):
        raise LLMUnavailable("ollama unreachable")

    async def stream(self, *args, **kwargs):
        raise LLMUnavailable("ollama unreachable")
        yield ""  # pragma: no cover - marks this as an async generator

    async def ping(self):
        return False


def parse_sse(text: str) -> list[tuple[str, dict]]:
    events: list[tuple[str, dict]] = []
    for block in text.split("\n\n"):
        block = block.strip()
        if not block:
            continue
        event_type = None
        data = None
        for line in block.split("\n"):
            if line.startswith("event:"):
                event_type = line[len("event:"):].strip()
            elif line.startswith("data:"):
                data = line[len("data:"):].strip()
        if event_type is not None:
            events.append((event_type, json.loads(data) if data else {}))
    return events
