"""AI provider protocol — swap implementations (Bedrock, OpenAI, Claude) without touching callers.
Source: extracted from Entertainment-App-Code-v1-4 reference build (ai/provider.py)
"""
from typing import Protocol, Optional


class AIProvider(Protocol):
    def extract_event_json(
        self, text: str, schema_json: dict, system_prompt: Optional[str] = None
    ) -> Optional[dict]:
        ...
