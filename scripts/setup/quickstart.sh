#!/usr/bin/env bash
set -euo pipefail

echo "═══════════════════════════════════════════════════"
echo "   SCI Research Platform — Quick Start Setup"
echo "═══════════════════════════════════════════════════"

# Check prerequisites
command -v docker >/dev/null 2>&1 || { echo "Docker is required. Install from https://docker.com"; exit 1; }
command -v docker-compose >/dev/null 2>&1 || { echo "Docker Compose is required."; exit 1; }

# Copy .env if it doesn't exist
if [ ! -f .env ]; then
    cp .env.example .env
    echo "Created .env from .env.example"
    echo "⚠  IMPORTANT: Edit .env with your API keys before continuing"
    echo ""
    echo "Required keys:"
    echo "  - ANTHROPIC_API_KEY (get from console.anthropic.com)"
    echo "  - CLERK_SECRET_KEY + CLERK_PUBLISHABLE_KEY (get from clerk.com)"
    echo "  - TAVILY_API_KEY (get from tavily.com)"
    echo ""
    read -p "Press ENTER after editing .env to continue..."
fi

# Generate secret key if placeholder
SECRET_KEY=$(grep SECRET_KEY .env | cut -d= -f2)
if [[ "$SECRET_KEY" == *"generate"* ]] || [ -z "$SECRET_KEY" ]; then
    NEW_KEY=$(openssl rand -hex 32)
    sed -i "s|<generate-with.*>|${NEW_KEY}|g" .env
    echo "Generated SECRET_KEY"
fi

echo ""
echo "Starting services..."
docker-compose pull
docker-compose up -d postgres redis

echo "Waiting for PostgreSQL to be ready..."
sleep 8

echo "Running database migrations..."
docker-compose run --rm backend alembic upgrade head

echo "Starting all services..."
docker-compose up -d

echo ""
echo "═══════════════════════════════════════════════════"
echo "   Platform is starting up!"
echo "═══════════════════════════════════════════════════"
echo ""
echo "  Frontend:    http://localhost:3000"
echo "  API Docs:    http://localhost:8000/api/docs"
echo "  Grafana:     http://localhost:3001"
echo "  Flower:      http://localhost:5555"
echo "  MinIO:       http://localhost:9001"
echo ""
echo "Run 'docker-compose logs -f' to monitor startup"
