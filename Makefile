# Makefile for Social Suit Docker operations

.PHONY: up down build logs ps clean help

help:
	@echo "Available commands:"
	@echo "  make up      - Start all services"
	@echo "  make down    - Stop and remove all services"
	@echo "  make build   - Build or rebuild services"
	@echo "  make logs    - View output from containers"
	@echo "  make ps      - List running containers"
	@echo "  make clean   - Remove all containers, networks, and volumes"

up:
	@echo "Starting Social Suit services..."
	docker-compose up -d
	@echo "Services started. API available at http://localhost:8000"
	@echo "Health check endpoint: http://localhost:8000/healthz"

down:
	@echo "Stopping Social Suit services..."
	docker-compose down
	@echo "Services stopped."

build:
	@echo "Building Social Suit services..."
	docker-compose build
	@echo "Build complete."

logs:
	docker-compose logs -f

ps:
	docker-compose ps

clean:
	@echo "Removing all containers, networks, and volumes..."
	docker-compose down -v --remove-orphans
	@echo "Clean complete."