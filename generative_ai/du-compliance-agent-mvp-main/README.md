# Compliance Agent MVP

MVP for checking documents against the TDRA regulatory and policy knowledge. You upload one or more documents (e.g. product specs, terms, process docs), choose which regulations to check against, and the app uses an LLM to produce a **compliance report**: a list of issues with evidence, severity, and recommendations.

**What it does in practice:**

- **Upload** documents (PDF, Word, etc.; converted to text for analysis).
- **Optional gatekeeper**: an LLM can quickly judge whether each document is relevant to compliance (e.g. skip clearly irrelevant files).
- **Select regulations**: use the built-in knowledge base (UAE telecom/domain/consumer regulations and policies) and/or attach your own policy files.
- **Run evaluation**: for each document × regulation, the LLM compares the text to the regulation, interprets mandatory language (must/shall/required), and only flags real gaps—non-compliance, missing requirements, or misalignment—with clause references and suggested fixes.
- **View results** in a table (issues, criticality, evidence, recommendations); you can tune columns and prompts.

The stack is a React frontend and a FastAPI server that talks to an LLM via either the DataRobot LLM Gateway or a direct OpenAI-compatible endpoint.

## Repo structure

| Path | Purpose |
|------|--------|
| `frontend/` | React + Vite + TypeScript UI (compliance wizard, table, file drop) |
| `server/` | FastAPI app: compliance API, knowledge-base, LLM client, file handling |
| `server/app/knowledge-base/` | Policy/regulation markdown used for compliance checks |
| `Architecture/` | Architecture docs and diagrams |

## Prerequisites

- **Node.js** (for frontend)
- **Python 3** (for server; see `server/requirements.txt`)
- **Docker** (optional; for `make run`)

## Quick start

### 1. Environment

```bash
cp server/.env.example server/.env
```

Edit `server/.env` and set either:

- **DataRobot Gateway:** `MODE=dr-gateway`, `DATAROBOT_ENDPOINT`, `DATAROBOT_API_TOKEN`
- **Direct LLM:** `MODE=direct-llm`, `LLM_ENDPOINT`, `LLM_API_KEY`

Optionally set `CHAT_COMPLETIONS_MODEL` (default `gpt-4o-mini`) and other options.

### 2. Run (local)

**Terminal 1 – server**

```bash
cd server
python -m venv .venv
source .venv/bin/activate   # or .venv\Scripts\activate on Windows
pip install -r requirements.txt
python main.py
```

**Terminal 2 – frontend**

```bash
cd frontend
npm install
npm run build
```

The Vite build outputs to `server/app/frontend_dist/`, which the server serves. Then open **http://localhost:8080**. For frontend-only dev with hot reload, run `npm run dev` in `frontend/` and use the Vite dev URL (you’ll need the server running on 8080 for API calls).

### 3. Run (Docker)

Build the app image and run the stack:

```bash
make build-env
make run
```

This builds the frontend, runs the server in the `app_env` container on port 8080, and mounts the repo so the server can serve the built frontend. Open **http://localhost:8080**.

## Other Make targets

- `make package` – build frontend and create `server.tar.gz` (excludes venv and `__pycache__`).

## Reference

- **API/docs:** when the server is running, see `http://localhost:8080/docs`.
- **Architecture:** `Architecture/README.md` and `Architecture/ARCHITECTURE.md`.
