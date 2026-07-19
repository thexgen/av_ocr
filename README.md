# Asset Vantage (`av_ocr`)

Wealth OS frontend + bank-statement processing engine + Jessy RAG chatbot.

## Layout

```
av_ocr/
  frontend/     # React (Vite + Tailwind)
  backend/      # FastAPI (OCR pipeline + Jessy)
```

## Stack

- Frontend: React 19, TypeScript, Vite, Tailwind v4, Framer Motion
- Backend: FastAPI, MySQL (bank cash), Qwen (mapping + Jessy), Qdrant (Jessy vectors)

## Run

```bash
# Frontend
cd frontend
npm install
npm run dev

# Backend (from av_ocr root)
pip install -r backend/requirements.txt
uvicorn backend.api.app:app --reload --host 127.0.0.1 --port 8000
```

Jessy also needs local Qdrant at `QDRANT_URL` (default `http://localhost:6333`) and `QWEN_API_KEY` in `backend/.env`.

See `torun.md` for a short cheat sheet.

## Key routes

| Route | Description |
|-------|-------------|
| `/` | Dashboard |
| `/transactions/bank-cash` | Ledger + statement upload |
| `/settings/knowledge-repository` | Jessy knowledge PDFs (admin) |

Floating Jessy chat is available on every page (chat history survives navigation).
