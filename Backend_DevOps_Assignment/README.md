# Transaction Intelligence Pipeline — Backend & DevOps Assignment

This repository contains a demo transaction-processing pipeline implemented with FastAPI, Celery, Redis, and PostgreSQL. It includes an automated runner that uploads a sample CSV, waits for processing, and writes results to `output/runner_output.json` for easy submission.

What's included
- `app/` — FastAPI app, Celery task wiring, processor, and LLM adapter.
- `docker-compose.yml` — Bring up API, worker, Redis, Postgres, Celery Flower, and the automated runner with a single command.
- `runner.py` — Automated demo script used by the `runner` service in docker-compose.
- `sample.csv` — Example input CSV.
- `output/runner_output.json` — Demo result (now tracked) — this file is the primary artifact graders can inspect.
- `tests/` — unit tests for the processor module.

Quick demo (single-command)
1. Ensure Docker and Docker Compose are installed.
2. From the project root run:

```bash
docker compose up --build
```

This will build images, start Postgres, Redis, API, worker and the runner. The runner uploads `sample.csv`, polls for completion, prints a summary to the logs, and writes `output/runner_output.json` to the project folder.

What to check for submission
- `output/runner_output.json` — human-friendly results with cleaned transactions, anomalies, category breakdown and narrative.
- `app/` — source code for API, worker, processor, and LLM adapter.
- `docker-compose.yml` and `Dockerfile`/`worker.Dockerfile` — how the services are containerized.
- `tests/` — small unit tests; run `pytest` locally if you want to re-run them.

Run tests locally (optional)
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pytest -q
```

Notes for graders
- The LLM adapter (`app/llm.py`) is optional and controlled by env `USE_GEMINI`. The project includes a deterministic heuristic fallback so results are reproducible without external LLM access.
- If you wish to re-run the end-to-end demo without Docker, see `run_job_once.py` for a small script that posts `sample.csv` to the API and polls for results.

Contact / Support
If anything in the demo fails on your environment, open an issue in this PR or contact me and I will reproduce or provide a standalone export.
