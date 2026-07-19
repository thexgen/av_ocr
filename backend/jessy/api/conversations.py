"""Conversation CRUD for ChatGPT-style Jessy history."""

from fastapi import APIRouter, HTTPException

from backend.db.connection import DatabaseError
from backend.jessy import db as jessy_db
from backend.jessy.schemas import ConversationCreate

router = APIRouter(prefix="/conversations", tags=["jessy-conversations"])


@router.get("")
def list_conversations() -> dict:
    try:
        items = jessy_db.list_conversations()
    except DatabaseError as exc:
        raise HTTPException(status_code=503, detail=exc.message) from exc
    return {"conversations": items}


@router.post("")
def create_conversation(body: ConversationCreate = ConversationCreate()) -> dict:
    try:
        conv = jessy_db.create_conversation(title=body.title or "New chat")
    except DatabaseError as exc:
        raise HTTPException(status_code=503, detail=exc.message) from exc
    return conv


@router.get("/{conversation_id}")
def get_conversation(conversation_id: int) -> dict:
    try:
        conv = jessy_db.get_conversation(conversation_id)
        if conv is None:
            raise HTTPException(status_code=404, detail="Conversation not found")
        messages = jessy_db.list_messages(conversation_id)
    except DatabaseError as exc:
        raise HTTPException(status_code=503, detail=exc.message) from exc
    return {"conversation": conv, "messages": messages}


@router.delete("/{conversation_id}")
def delete_conversation(conversation_id: int) -> dict:
    try:
        deleted = jessy_db.delete_conversation(conversation_id)
    except DatabaseError as exc:
        raise HTTPException(status_code=503, detail=exc.message) from exc
    if not deleted:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {"success": True, "id": conversation_id}
