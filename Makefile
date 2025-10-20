.PHONY: help build up down restart logs shell test clean

# Default target
help:
	@echo "Available commands:"
	@echo "  make build          - Build Docker images"
	@echo "  make up             - Start all services"
	@echo "  make down           - Stop all services"
	@echo "  make restart        - Restart all services"
	@echo "  make logs           - View logs"
	@echo "  make logs-api       - View API logs only"
	@echo "  make logs-db        - View MySQL logs only"
	@echo "  make shell          - Open shell in API container"
	@echo "  make shell-db       - Open MySQL shell"
	@echo "  make test           - Run tests"
	@echo "  make clean          - Remove containers, volumes, and images"
	@echo ""
	@echo "Development commands:"
	@echo "  make dev-build      - Build development images"
	@echo "  make dev-up         - Start development environment with hot-reload"
	@echo "  make dev-down       - Stop development environment"
	@echo "  make dev-logs       - View development logs"
	@echo "  make dev-shell      - Open shell in development API container"

# Production commands
build:
	docker-compose build

up:
	docker-compose up -d

down:
	docker-compose down

restart:
	docker-compose restart

logs:
	docker-compose logs -f

logs-api:
	docker-compose logs -f api

logs-db:
	docker-compose logs -f mysql

shell:
	docker-compose exec api /bin/bash

shell-db:
	docker-compose exec mysql mysql -u$(MYSQL_USER) -p$(MYSQL_PASSWORD)

test:
	docker-compose exec api pytest

clean:
	docker-compose down -v --rmi all

# Development commands
dev-build:
	docker-compose -f docker-compose.dev.yml build

dev-up:
	docker-compose -f docker-compose.dev.yml up -d

dev-down:
	docker-compose -f docker-compose.dev.yml down

dev-restart:
	docker-compose -f docker-compose.dev.yml restart

dev-logs:
	docker-compose -f docker-compose.dev.yml logs -f

dev-logs-api:
	docker-compose -f docker-compose.dev.yml logs -f api

dev-shell:
	docker-compose -f docker-compose.dev.yml exec api /bin/bash

dev-shell-db:
	docker-compose -f docker-compose.dev.yml exec mysql mysql -u$(MYSQL_USER) -p$(MYSQL_PASSWORD)

dev-test:
	docker-compose -f docker-compose.dev.yml exec api pytest

dev-clean:
	docker-compose -f docker-compose.dev.yml down -v --rmi all

# Database commands
db-migrate:
	docker-compose exec api alembic upgrade head

db-migrate-dev:
	docker-compose -f docker-compose.dev.yml exec api alembic upgrade head

db-revision:
	docker-compose exec api alembic revision --autogenerate -m "$(msg)"

db-revision-dev:
	docker-compose -f docker-compose.dev.yml exec api alembic revision --autogenerate -m "$(msg)"

# Utility commands
ps:
	docker-compose ps

ps-dev:
	docker-compose -f docker-compose.dev.yml ps

prune:
	docker system prune -af --volumes
