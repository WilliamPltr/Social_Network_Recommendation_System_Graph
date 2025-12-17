PYTHON ?= python

.PHONY: up down logs api tests lint etl-snap etl-jobs etl-user-emb

help:
	@echo "Available make commands:"
	@echo "  make up           - Build and start all Docker services"
	@echo "  make down         - Stop and remove Docker services"
	@echo "  make logs         - Tail Docker logs"
	@echo "  make api          - Run the FastAPI app locally with uvicorn"
	@echo "  make tests        - Run pytest test suite"
	@echo "  make lint         - Run pylint on app, scripts, and tests"
	@echo "  make etl-snap     - Load SNAP GitHub data into Neo4j"
	@echo "  make etl-jobs     - Load LinkedIn job listings into Neo4j"
	@echo "  make etl-user-emb - Create user embeddings in Neo4j"
	@echo "  make begin        - Load all data into Neo4j"
	@echo "  make pip          - Install dependencies"

up:
	docker compose up --build

down:
	docker compose down -v

logs:
	docker compose logs -f

api:
	$(PYTHON) -m uvicorn app.main:app --reload

tests:
	$(PYTHON) -m pytest -q

lint:
	$(PYTHON) -m pylint app scripts tests --exit-zero || true

etl-snap:
	$(PYTHON) -m scripts.load_snap

etl-jobs:
	$(PYTHON) -m scripts.load_jobs

etl-user-emb:
	$(PYTHON) -m scripts.create_user_embeddings

begin:
	make etl-snap
	make etl-jobs
	make etl-user-emb

pip:
	pip install -r requirements.txt