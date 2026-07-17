"""
LLM client helpers + back-compat export for mapping.

Prefer: poc.pipeline.mapping_engine.resolve_field_mapping
"""

from __future__ import annotations

from poc.pipeline.mapping_engine import call_qwen_for_mapping, resolve_field_mapping

__all__ = ["call_qwen_for_mapping", "resolve_field_mapping"]
