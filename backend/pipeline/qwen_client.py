"""
Back-compat export for mapping.

Prefer: backend.pipeline.mapping_engine.resolve_field_mapping
(LLM backend is Amazon Bedrock Nova Lite.)
"""

from __future__ import annotations

from backend.pipeline.mapping_engine import call_qwen_for_mapping, resolve_field_mapping

__all__ = ["call_qwen_for_mapping", "resolve_field_mapping"]
