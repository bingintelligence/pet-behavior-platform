SHELL := /bin/bash

PROJECT_NAME := pet-behavior-platform
PYTHON := python3
UV := uv
DOCKER_COMPOSE := docker compose

.DEFAULT_GOAL := help

.PHONY: help install install-dev sync format format-check lint type-check test test-unit test-integration 
test-cov check run dev stop restart build rebuild logs ps clean clean-python clean-docker 
db-migrate db-upgrade db-downgrade db-reset kafka-topics prometheus-check

help:
@echo ""
@echo "$(PROJECT_NAME)"
@echo ""
@echo "Available commands:"
@echo "  make install           Install production dependencies"
@echo "  make install-dev       Install development dependencies"
@echo "  make sync              Synchronize dependencies from lock file"
@echo "  make format            Format Python code"
@echo "  make format-check      Check Python formatting"
@echo "  make lint              Run Ruff linting"
@echo "  make type-check        Run Mypy type checking"
@echo "  make test              Run all tests"
@echo "  make test-unit         Run unit tests"
@echo "  make test-integration  Run integration tests"
@echo "  make test-cov          Run tests with coverage"
@echo "  make check             Run formatting, linting, typing, and tests"
@echo "  make run               Run API locally"
@echo "  make dev               Start local development stack"
@echo "  make stop              Stop local development stack"
@echo "  make restart           Restart local development stack"
@echo "  make build             Build Docker images"
@echo "  make rebuild           Rebuild and restart Docker services"
@echo "  make logs              Follow Docker Compose logs"
@echo "  make ps                Show running services"
@echo "  make clean             Remove local generated files"
@echo "  make clean-docker      Remove Docker containers and volumes"
@echo "  make db-migrate        Create a new Alembic migration"
@echo "  make db-upgrade        Apply database migrations"
@echo "  make db-downgrade      Roll back one database migration"
@echo "  make db-reset          Recreate the local database"

install:
$(UV) sync --no-dev

install-dev:
$(UV) sync --all-groups

sync:
$(UV) sync --frozen --all-groups

format:
$(UV) run ruff format .
$(UV) run ruff check . --fix

format-check:
$(UV) run ruff format . --check

lint:
$(UV) run ruff check .

type-check:
$(UV) run mypy services workers shared

test:
$(UV) run pytest

test-unit:
$(UV) run pytest tests/unit -m unit

test-integration:
$(UV) run pytest tests/integration -m integration

test-cov:
$(UV) run pytest 
--cov=services 
--cov=workers 
--cov=shared 
--cov-report=term-missing 
--cov-report=html 
--cov-fail-under=80

check: format-check lint type-check test

run:
$(UV) run uvicorn services.api_gateway.src.main:app 
--host 0.0.0.0 
--port 8000 
--reload

dev:
$(DOCKER_COMPOSE) up -d --build

stop:
$(DOCKER_COMPOSE) down

restart:
$(DOCKER_COMPOSE) restart

build:
$(DOCKER_COMPOSE) build

rebuild:
$(DOCKER_COMPOSE) down
$(DOCKER_COMPOSE) up -d --build --force-recreate

logs:
$(DOCKER_COMPOSE) logs -f --tail=200

ps:
$(DOCKER_COMPOSE) ps

clean: clean-python
rm -rf htmlcov
rm -rf coverage.xml
rm -rf .coverage
rm -rf dist
rm -rf build

clean-python:
find . -type d -name "**pycache**" -prune -exec rm -rf {} +
find . -type d -name ".pytest_cache" -prune -exec rm -rf {} +
find . -type d -name ".mypy_cache" -prune -exec rm -rf {} +
find . -type d -name ".ruff_cache" -prune -exec rm -rf {} +
find . -type f -name "*.pyc" -delete

clean-docker:
$(DOCKER_COMPOSE) down --volumes --remove-orphans
docker image prune -f

db-migrate:
@test -n "$(MESSAGE)" || 
(echo "Usage: make db-migrate MESSAGE='describe change'" && exit 1)
$(UV) run alembic revision --autogenerate -m "$(MESSAGE)"

db-upgrade:
$(UV) run alembic upgrade head

db-downgrade:
$(UV) run alembic downgrade -1

db-reset:
$(DOCKER_COMPOSE) stop postgres
$(DOCKER_COMPOSE) rm -f postgres
docker volume rm $(PROJECT_NAME)_postgres_data 2>/dev/null || true
$(DOCKER_COMPOSE) up -d postgres
@echo "Waiting for PostgreSQL..."
@sleep 5
$(UV) run alembic upgrade head

kafka-topics:
$(DOCKER_COMPOSE) exec kafka kafka-topics.sh 
--bootstrap-server localhost:9092 
--list

prometheus-check:
curl --fail http://localhost:9090/-/healthy
