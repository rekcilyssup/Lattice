# Demo Commands

## Start services

```bash
cd BackendFastAPI
cp .env.example .env
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m app.db.migrate
uvicorn app.main:app --reload --port 8080
```

In another terminal:

```bash
cd Frontend
npm run dev
```

## API smoke test

```bash
curl http://localhost:8080/api/v1/health
```

## Create workspace

```bash
curl -X POST http://localhost:8080/api/v1/workspaces \
  -H 'Content-Type: application/json' \
  -d '{"name":"SupportBot Demo"}'
```

## Upload PDF

```bash
curl -X POST http://localhost:8080/api/v1/workspaces/<WORKSPACE_ID>/documents/upload \
  -F "file=@/Users/aravindrao/Downloads/Case Study_ AI for Sustainable Development in Visakhapatnam.pdf"
```

## Ask question

```bash
curl -X POST http://localhost:8080/api/v1/workspaces/<WORKSPACE_ID>/chat \
  -H 'Content-Type: application/json' \
  -d '{"query":"What is Visakhapatnam famous for?"}'
```

Look for these fields in response:

- `answer`
- `citations[]`
- `sources[]`
- `retrieval.latencyMs`

