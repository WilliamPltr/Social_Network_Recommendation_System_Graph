PYTHON ?= python

.PHONY: up down logs api tests lint etl-snap etl-jobs etl-user-emb

up:
	docker compose up --build

down:
	docker compose down -v

logs:
	docker compose logs -f

api:
	$(PYTHON) -m uvicorn app.main:app --reload

tests:
	pytest -q

etl-snap:
	$(PYTHON) -m scripts.load_snap

etl-jobs:
	$(PYTHON) -m scripts.load_jobs

etl-user-emb:
	$(PYTHON) -m scripts.create_user_embeddings


