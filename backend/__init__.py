"""
Asset Vantage backend — statement OCR engine + Jessy RAG.

Architecture:
  api/          — FastAPI app (statement jobs + Jessy routes)
  pipeline/     — bank-statement processing
  jessy/        — RAG chatbot (upload → embed → Qdrant → Qwen)
  db/           — MySQL staging / bankcash
  interfaces/   — storage ports
  services/     — storage adapters
"""
