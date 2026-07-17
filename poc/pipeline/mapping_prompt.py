from __future__ import annotations

from poc.config import STANDARD_SCHEMA

UNKNOWN_HEADERS_SYSTEM_PROMPT = """You are a financial field-mapping assistant.

Map ONLY the unknown column headers to the closest field in our standard schema.

Rules:
- Return ONLY valid JSON. No markdown. No commentary.
- Do not invent values or change header strings.
- Keys in field_mapping MUST be the exact header strings from the input list.
- If a header cannot be mapped confidently, omit it.
- Never map utility columns like LineNo / row numbers.

STANDARD SCHEMA
""" + ", ".join(STANDARD_SCHEMA) + """

OUTPUT FORMAT (exact keys):
{
  "field_mapping": {
    "<exact unknown header>": "<StandardSchemaField>"
  },
  "confidence": 0,
  "warnings": []
}
"""


def build_unknown_headers_prompt(unknown_headers: list[str]) -> str:
    return (
        "Map these unknown headers to the closest field in our standard schema.\n"
        "Return only JSON.\n\n"
        f"Unknown headers:\n{unknown_headers}\n"
    )


# Back-compat for any older imports
MAPPING_SYSTEM_PROMPT = UNKNOWN_HEADERS_SYSTEM_PROMPT


def build_user_prompt(metadata: dict, headers: list[str], sample_rows: list[dict]) -> str:
    """Deprecated full-document prompt — unknown-headers path is preferred."""
    return build_unknown_headers_prompt(headers)
