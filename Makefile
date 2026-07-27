.PHONY: backend-install backend-run frontend-install frontend-run test eval health integrations

backend-install:
	cd backend && python -m venv .venv && (.venv/Scripts/pip install -r requirements.txt || .venv/bin/pip install -r requirements.txt)

backend-run:
	cd backend && uvicorn app.main:app --reload --port 8100

frontend-install:
	cd frontend && npm install

frontend-run:
	cd frontend && npm run dev

test:
	cd backend && pytest

eval:
	cd backend && (.venv/Scripts/python -m app.eval.cli || .venv/bin/python -m app.eval.cli)

health:
	curl -s http://localhost:8100/api/health

integrations:
	curl -s http://localhost:8100/api/integrations
