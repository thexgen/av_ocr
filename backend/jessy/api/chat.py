"""Jessy chat + search API (RAG: retrieve → Qwen → answer)."""

from fastapi import APIRouter

from backend.jessy.llm import generate_rag_answer
from backend.jessy.schemas import ChatRequest, ChatResponse
from backend.jessy.utils.vector_search import search_similar_chunks

router = APIRouter(tags=["jessy-chat"])


@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    """Retrieve relevant chunks, then generate a grounded answer with Qwen."""
    matches = search_similar_chunks(request.question)

    if not matches:
        return ChatResponse(
            answer=(
                "I could not find relevant information in the knowledge base "
                "for that question. Try uploading related PDFs in Knowledge Repository."
            ),
            sources=[],
        )

    context_parts: list[str] = []
    sources: list[str] = []
    for match in matches:
        file_name = str(match.get("file_name") or "document")
        content = str(match.get("content") or "").strip()
        if content:
            context_parts.append(f"[{file_name}]\n{content}")
        if file_name and file_name not in sources:
            sources.append(file_name)

    answer = generate_rag_answer(request.question, "\n\n".join(context_parts))
    return ChatResponse(answer=answer, sources=sources)


@router.post("/search")
def search(request: ChatRequest) -> dict[str, list[dict[str, object]]]:
    """Return top semantic matches for a question (debug / future UI)."""
    matches = search_similar_chunks(request.question)
    return {"matches": matches}
