"""Jessy RAG answer generation via Amazon Bedrock Nova Lite."""

from __future__ import annotations

import logging
import re

from backend.config import LLM_MAX_INPUT_CHARS, LLM_MAX_TOKENS
from backend.llm.bedrock_client import bedrock_configured, get_bedrock_client

logger = logging.getLogger("jessy")

SYSTEM_PROMPT = """You are Jessy, a helpful wealth-management knowledge assistant.
Answer ONLY using the provided context from the knowledge repository.
If the context is insufficient, say you do not have enough information in the knowledge base.
Be concise, accurate, and professional. Do not invent facts."""

TITLE_SYSTEM_PROMPT = """You name chat conversations for a wealth-management assistant.
Return ONLY a short, clear title (3–6 words). No quotes, no punctuation at the end, no explanations."""


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


def _fallback_title(question: str) -> str:
    title = " ".join(question.strip().split())
    if not title:
        return "New chat"
    if len(title) > 60:
        return title[:57] + "..."
    return title


def _clean_title(raw: str, *, fallback: str) -> str:
    title = (raw or "").strip().strip("\"'`")
    title = re.sub(r"[\r\n]+", " ", title)
    title = re.sub(r"^(title\s*:\s*)", "", title, flags=re.IGNORECASE)
    title = " ".join(title.split())
    if not title:
        return fallback
    if len(title) > 60:
        title = title[:57] + "..."
    return title


def generate_conversation_title(question: str, answer: str = "") -> str:
    """AI short title for a chat thread; falls back to truncated question."""
    fallback = _fallback_title(question)
    if not bedrock_configured():
        return fallback

    clipped_answer = (answer or "").strip()
    if len(clipped_answer) > 400:
        clipped_answer = clipped_answer[:400] + "..."

    prompt = (
        f"User message:\n{question.strip()}\n\n"
        f"Assistant reply (excerpt):\n{clipped_answer or '(none)'}\n\n"
        "Suggest a short chat title."
    )

    try:
        client = get_bedrock_client()
        raw = client.invoke_text(
            prompt,
            system=TITLE_SYSTEM_PROMPT,
            temperature=0.3,
            max_tokens=32,
        )
        return _clean_title(raw, fallback=fallback)
    except Exception:  # noqa: BLE001
        logger.exception("Jessy title generation failed")
        return fallback
