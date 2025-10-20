#!/bin/bash
# Quick start script for Linux/macOS

set -e

echo "🐳 SOAT v2 - Quick Start Script"
echo "================================"
echo ""

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    echo "Visit: https://docs.docker.com/get-docker/"
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose first."
    echo "Visit: https://docs.docker.com/compose/install/"
    exit 1
fi

echo "✅ Docker and Docker Compose are installed"
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo "📝 Creating .env file from .env.example..."
    cp .env.example .env
    echo "✅ .env file created"
    echo "⚠️  Please edit .env file with your configuration"
    echo ""
else
    echo "✅ .env file already exists"
    echo ""
fi

# Ask user which mode
echo "Select mode:"
echo "1) Development (with hot-reload)"
echo "2) Production"
read -p "Enter choice [1-2]: " choice

case $choice in
    1)
        echo ""
        echo "🔨 Starting in DEVELOPMENT mode..."
        echo "=================================="
        echo ""
        echo "Building images..."
        docker-compose -f docker-compose.dev.yml build
        echo ""
        echo "Starting services..."
        docker-compose -f docker-compose.dev.yml up -d
        echo ""
        echo "✅ Services started!"
        echo ""
        echo "📊 Service Status:"
        docker-compose -f docker-compose.dev.yml ps
        echo ""
        echo "🌐 Access URLs:"
        echo "  - API:        http://localhost:8000"
        echo "  - Swagger:    http://localhost:8000/api/docs"
        echo "  - ReDoc:      http://localhost:8000/api/redoc"
        echo "  - Health:     http://localhost:8000/api/v1/health"
        echo "  - phpMyAdmin: http://localhost:8080"
        echo ""
        echo "📝 Useful commands:"
        echo "  - View logs:      docker-compose -f docker-compose.dev.yml logs -f"
        echo "  - Stop services:  docker-compose -f docker-compose.dev.yml down"
        echo "  - Restart:        docker-compose -f docker-compose.dev.yml restart"
        echo "  - Shell:          docker-compose -f docker-compose.dev.yml exec api bash"
        echo ""
        ;;
    2)
        echo ""
        echo "🚀 Starting in PRODUCTION mode..."
        echo "=================================="
        echo ""
        echo "Building images..."
        docker-compose build
        echo ""
        echo "Starting services..."
        docker-compose up -d
        echo ""
        echo "✅ Services started!"
        echo ""
        echo "📊 Service Status:"
        docker-compose ps
        echo ""
        echo "🌐 Access URLs:"
        echo "  - API:     http://localhost:8000"
        echo "  - Health:  http://localhost:8000/api/v1/health"
        echo ""
        echo "📝 Useful commands:"
        echo "  - View logs:      docker-compose logs -f"
        echo "  - Stop services:  docker-compose down"
        echo "  - Restart:        docker-compose restart"
        echo "  - Shell:          docker-compose exec api bash"
        echo ""
        ;;
    *)
        echo "❌ Invalid choice. Exiting."
        exit 1
        ;;
esac

echo "🎉 Setup complete! Happy coding!"
