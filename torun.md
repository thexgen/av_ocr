# Frontend
cd frontend
npm run dev

# Backend (from av_ocr root)
uvicorn backend.api.app:app --reload --host 127.0.0.1 --port 8000

# Jessy needs local Qdrant (http://localhost:6333)
# LLM: Amazon Bedrock Nova Lite — AWS_* + BEDROCK_* in backend/.env
