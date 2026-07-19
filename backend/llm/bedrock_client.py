"""Amazon Bedrock Nova Lite client via Converse API."""

from __future__ import annotations

import logging
import os
from functools import lru_cache

logger = logging.getLogger("holding_engine")


class BedrockClient:
    """Thin wrapper around boto3 bedrock-runtime Converse."""

    def __init__(
        self,
        *,
        region: str,
        model_id: str,
        max_tokens: int = 512,
        access_key_id: str | None = None,
        secret_access_key: str | None = None,
    ) -> None:
        import boto3

        kwargs: dict = {"region_name": region}
        if access_key_id and secret_access_key:
            kwargs["aws_access_key_id"] = access_key_id
            kwargs["aws_secret_access_key"] = secret_access_key

        self._client = boto3.client("bedrock-runtime", **kwargs)
        self.model_id = model_id
        self.max_tokens = max_tokens

    def invoke_text(
        self,
        prompt: str,
        *,
        system: str | None = None,
        temperature: float = 0.0,
        max_tokens: int | None = None,
    ) -> str:
        """Send a prompt and return plain assistant text."""
        kwargs: dict = {
            "modelId": self.model_id,
            "messages": [
                {
                    "role": "user",
                    "content": [{"text": prompt}],
                }
            ],
            "inferenceConfig": {
                "temperature": temperature,
                "maxTokens": max_tokens or self.max_tokens,
            },
        }
        if system:
            kwargs["system"] = [{"text": system}]

        logger.info("Bedrock Converse model=%s", self.model_id)
        response = self._client.converse(**kwargs)
        parts = response.get("output", {}).get("message", {}).get("content", [])
        texts = [p.get("text", "") for p in parts if isinstance(p, dict) and p.get("text")]
        return "\n".join(texts).strip()


@lru_cache(maxsize=1)
def get_bedrock_client() -> BedrockClient:
    """Cached client from env / config."""
    from backend.config import (
        AWS_ACCESS_KEY_ID,
        AWS_SECRET_ACCESS_KEY,
        BEDROCK_MODEL_ID,
        BEDROCK_REGION,
        LLM_MAX_TOKENS,
    )

    return BedrockClient(
        region=BEDROCK_REGION,
        model_id=BEDROCK_MODEL_ID,
        max_tokens=LLM_MAX_TOKENS,
        access_key_id=AWS_ACCESS_KEY_ID or None,
        secret_access_key=AWS_SECRET_ACCESS_KEY or None,
    )


def bedrock_configured() -> bool:
    """True when model id is set and credentials exist (env or default chain)."""
    from backend.config import AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, BEDROCK_MODEL_ID

    if not BEDROCK_MODEL_ID:
        return False
    if AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY:
        return True
    # Allow default AWS credential chain (~/.aws/credentials, IAM role)
    return bool(os.getenv("AWS_PROFILE") or os.path.exists(os.path.expanduser("~/.aws/credentials")))
