"""Shared LLM clients (Amazon Bedrock)."""

from backend.llm.bedrock_client import BedrockClient, get_bedrock_client

__all__ = ["BedrockClient", "get_bedrock_client"]
