.PHONY: backend frontend test build run

backend:
	cd backend && python -m pip install -r requirements.txt && PYTHONPATH=. python -m uvicorn app.main:app --host 0.0.0.0 --port 8000

frontend:
	cd frontend && npm install && npm run dev

test:
	cd backend && PYTHONPATH=. python -m pytest -q

build:
	cd frontend && npm run build

run: test
	bash scripts/run_demo.sh
