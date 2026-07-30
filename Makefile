# Makefile for User-APP-Template

.PHONY: dev test lint db-up db-down sync-ai clean help migrate migrations

# --- Variables ---
PYTHON := python3
MANAGE := $(PYTHON) backend/manage.py

help:
	@echo "Usage: make [command]"
	@echo ""
	@echo "Commands:"
	@echo "  dev         Run the Django development server"
	@echo "  test        Run pytest on the backend apps"
	@echo "  lint        Run the 'ruff' linter/formatter"
	@echo "  db-up       Start PostgreSQL in Docker"
	@echo "  db-down     Stop the services"
	@echo "  migrate     Apply database migrations"
	@echo "  migrations  Create new migrations"
	@echo "  sync-ai     Update the Universal-Agents framework (.agents)"
	@echo "  clean       Remove temporary and cache files"

dev:
	@echo "Starting Development Server..."
	$(MANAGE) runserver

test:
	@echo "Running tests..."
	pytest backend/apps/users/tests.py

lint:
	@echo "Linting and Formatting..."
	ruff check backend/ --fix
	ruff format backend/

db-up:
	@echo "Spinning up Database..."
	docker compose up -d

db-down:
	@echo "Shutting down services..."
	docker compose down

migrate:
	@echo "Applying Migrations..."
	$(MANAGE) migrate

migrations:
	@echo "Detecting changes..."
	$(MANAGE) makemigrations

sync-ai:
	@echo "Syncing AI Constitutional Framework..."
	git submodule update --remote --merge

clean:
	@echo "Cleaning caches..."
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf .pytest_cache/
	rm -rf .ruff_cache/
