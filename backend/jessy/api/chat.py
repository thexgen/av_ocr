"""Jessy chat + search API (RAG + persisted conversations)."""

from fastapi import APIRouter, HTTPException

from backend.db.connection import DatabaseError
from backend.jessy import db as jessy_db
from backend.jessy.llm import generate_conversation_title, generate_rag_answer
from backend.jessy.schemas import ChatRequest, ChatResponse
from backend.jessy.utils.vector_search import search_similar_chunks

router = APIRouter(tags=["jessy-chat"])


@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    """Retrieve → answer → persist into a conversation thread."""
    try:
        needs_title = False
        if request.conversation_id is None:
            conv = jessy_db.create_conversation(title="New chat")
            conversation_id = int(conv["id"])
            needs_title = True
        else:
            existing = jessy_db.get_conversation(request.conversation_id)
            if existing is None:
                raise HTTPException(status_code=404, detail="Conversation not found")
            conversation_id = request.conversation_id
            needs_title = str(existing.get("title") or "") == "New chat"

        user_msg = jessy_db.add_message(
            conversation_id=conversation_id,
            role="user",
            content=request.question,
        )

        matches = search_similar_chunks(request.question)

        if not matches:
            answer = (
                "I could not find relevant information in the knowledge base "
                "for that question. Try uploading related PDFs in Knowledge Repository."
            )
            sources: list[str] = []
        else:
            context_parts: list[str] = []
            sources = []
            for match in matches:
                file_name = str(match.get("file_name") or "document")
                content = str(match.get("content") or "").strip()
                if content:
                    context_parts.append(f"[{file_name}]\n{content}")
                if file_name and file_name not in sources:
                    sources.append(file_name)
            answer = generate_rag_answer(request.question, "\n\n".join(context_parts))

        assistant_msg = jessy_db.add_message(
            conversation_id=conversation_id,
            role="assistant",
            content=answer,
            sources=sources,
        )

        title: str | None = None
        if needs_title:
            ai_title = generate_conversation_title(request.question, answer)
            title = jessy_db.maybe_set_ai_title(conversation_id, ai_title)
            if title is None:
                title = jessy_db.get_conversation_title(conversation_id)
    except DatabaseError as exc:
        raise HTTPException(status_code=503, detail=exc.message) from exc

    return ChatResponse(
        answer=answer,
        sources=sources,
        conversation_id=conversation_id,
        user_message_id=int(user_msg["id"]),
        assistant_message_id=int(assistant_msg["id"]),
        title=title,
    )


@router.post("/search")
def search(request: ChatRequest) -> dict[str, list[dict[str, object]]]:
    """Return top semantic matches for a question (debug / future UI)."""
    matches = search_similar_chunks(request.question)
    return {"matches": matches}
