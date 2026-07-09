"""Stub-friendly AI provider. Wire the real model (Claude API per master spec sec.14,
or AWS Bedrock) later — swap by implementing extract_event_json.
Source: extracted from Entertainment-App-Code-v1-4 reference build (ai/bedrock_provider.py)
"""
import json
from typing import Optional
from ai.provider import AIProvider
from ai.prompts import EXTRACTION_SYSTEM_PROMPT


class BedrockProvider(AIProvider):
    def __init__(self, client=None, model_id: str = "stub"):
        self.client = client
        self.model_id = model_id

    def extract_event_json(
        self, text: str, schema_json: dict, system_prompt: Optional[str] = None
    ) -> Optional[dict]:
        # If no client, return None (forces evidence-based/manual ops path).
        if self.client is None or self.model_id == "stub":
            return None
        payload = {
            "system": system_prompt or EXTRACTION_SYSTEM_PROMPT,
            "inputText": text,
            "schema": schema_json
        }
        resp = self.client.invoke_model(
            modelId=self.model_id,
            body=json.dumps(payload).encode("utf-8"),
            accept="application/json",
            contentType="application/json"
        )
        body = resp["body"].read()
        try:
            return json.loads(body.decode("utf-8"))
        except Exception:
            return None
