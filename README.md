# Aether Wealth — AI Statement Import

Enterprise React UI for an AI-powered investment statement import workflow.

## Stack

- React 19 + TypeScript
- Vite
- Tailwind CSS v4
- Framer Motion
- Lucide React
- React Router

## Pages

| Route | Description |
|-------|-------------|
| `/` | Dashboard — stats, recent imports, supported formats |
| `/upload` | Multi-file drag & drop upload queue |
| `/processing` | Animated AI processing pipeline |
| `/review` | Transaction table with detail drawer |
| `/success` | Import summary & report download |

## Run

```bash
npm install
npm run dev
```

Open the local URL printed by Vite (typically `http://localhost:5173`).

## Notes

- No backend — all data is mocked in `src/data/mockData.ts`
- Upload validation runs client-side (type + size)
- Processing steps are simulated, then auto-redirect to Review
