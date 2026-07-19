"""Aggregate Jessy routers for mounting on the main FastAPI app."""

from fastapi import APIRouter

from backend.jessy.api.attachments import router as attachments_router
from backend.jessy.api.chat import router as chat_router
from backend.jessy.api.conversations import router as conversations_router
from backend.jessy.api.documents import router as documents_router

router = APIRouter()
router.include_router(chat_router)
router.include_router(attachments_router)
router.include_router(conversations_router)
router.include_router(documents_router)
