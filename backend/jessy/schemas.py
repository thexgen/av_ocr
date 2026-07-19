"""Pydantic schemas for Jessy chat endpoints."""

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1, description="User question to process")
    conversation_id: int | None = Field(
        default=None,
        description="Existing conversation id; omit to start a new chat",
    )


class ChatResponse(BaseModel):
    answer: str = Field(..., description="Grounded answer from Jessy")
    sources: list[str] = Field(default_factory=list, description="Referenced source files")
    conversation_id: int = Field(..., description="Conversation this turn belongs to")
    user_message_id: int | None = None
    assistant_message_id: int | None = None
    title: str | None = Field(
        default=None,
        description="Conversation title (AI-generated on first turn when available)",
    )


class ConversationCreate(BaseModel):
    title: str = Field(default="New chat", max_length=255)


class ChatAttachmentFileInfo(BaseModel):
    file_name: str
    size: int
    content_type: str


class ChatAttachmentsResponse(BaseModel):
    """Phase 1 acknowledge-only response for chat file uploads."""

    status: str = "success"
    files_received: int
    file_name: str
    file_names: list[str] = Field(default_factory=list)
    files: list[ChatAttachmentFileInfo] = Field(default_factory=list)
    conversation_id: int | None = None
    message: str = ""

