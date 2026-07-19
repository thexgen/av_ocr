"""Pydantic schemas for Jessy chat endpoints."""

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1, description="User question to process")


class ChatResponse(BaseModel):
    answer: str = Field(..., description="Grounded answer from Jessy")
    sources: list[str] = Field(default_factory=list, description="Referenced source files")
