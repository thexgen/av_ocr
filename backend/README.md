# Holding Statement Processing Engine (local)

Production-ready **local** engine + minimal FastAPI API. No AWS / Lambda / DB.

```
backend/
  config.yaml
  sample_data/                # INPUT
  output/{JOB_ID}/            # OUTPUT per job
  api/                        # FastAPI (thin wrapper)
  engine.py                   # ProcessingEngine
  pipeline/                   # business processing
  interfaces/ + services/     # StorageService
```

## CLI

```bash
pip install -r backend\requirements.txt
python -m backend.main --create-sample
```

## API

```bash
uvicorn backend.api.app:app --reload --app-dir .
# or from repo root:
uvicorn backend.api:app --reload --host 127.0.0.1 --port 8000
```

### POST /upload

`multipart/form-data` field: `file` (holding PDF)

Response:

```json
{ "job_id": "JOB_20260717_000001", "status": "PROCESSING" }
```

### GET /job/{job_id}

Returns status, validation summary, CSV/JSON paths, processing duration.

### Docs

Open http://127.0.0.1:8000/docs
