"""Jessy RAG answer generation via Amazon Bedrock Nova Lite."""

from __future__ import annotations

import logging

from backend.config import LLM_MAX_INPUT_CHARS, LLM_MAX_TOKENS
from backend.llm.bedrock_client import bedrock_configured, get_bedrock_client

logger = logging.getLogger("jessy")

SYSTEM_PROMPT = """You are Jessy, a helpful wealth-management knowledge assistant.
Answer ONLY using the provided context from the knowledge repository.
If the context is insufficient, say you do not have enough information in the knowledge base.
Be concise, accurate, and professional. Do not invent facts."""


def generate_rag_answer(question: str, context: str) -> str:
    """Retrieve-context → Bedrock Converse → grounded answer text."""
    if not bedrock_configured():
        return (
            "Jessy LLM is not configured. Set AWS credentials and BEDROCK_MODEL_ID "
            "in backend/.env."
        )

    clipped_context = context
    if len(clipped_context) > LLM_MAX_INPUT_CHARS:
        clipped_context = clipped_context[:LLM_MAX_INPUT_CHARS]

    user_prompt = (
        f"Context from knowledge repository:\n\n{clipped_context}\n\n"
        f"Question: {question}\n\n"
        "Answer based only on the context above."
    )

    try:
        client = get_bedrock_client()
        return client.invoke_text(
            user_prompt,
            system=SYSTEM_PROMPT,
            temperature=0.2,
            max_tokens=LLM_MAX_TOKENS,
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("Jessy Bedrock call failed")
        return f"Sorry, Jessy could not generate an answer right now ({exc})."
