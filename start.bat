@echo off
REM Quick start script for Windows

echo.
echo ================================
echo 🐳 SOAT v2 - Quick Start Script
echo ================================
echo.

REM Check if Docker is installed
docker --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Docker is not installed. Please install Docker Desktop first.
    echo Visit: https://www.docker.com/products/docker-desktop
    pause
    exit /b 1
)

REM Check if Docker Compose is installed
docker-compose --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Docker Compose is not installed. Please install Docker Desktop first.
    echo Visit: https://www.docker.com/products/docker-desktop
    pause
    exit /b 1
)

echo ✅ Docker and Docker Compose are installed
echo.

REM Check if .env exists
if not exist .env (
    echo 📝 Creating .env file from .env.example...
    copy .env.example .env >nul
    echo ✅ .env file created
    echo ⚠️  Please edit .env file with your configuration
    echo.
) else (
    echo ✅ .env file already exists
    echo.
)

REM Ask user which mode
echo Select mode:
echo 1^) Development ^(with hot-reload^)
echo 2^) Production
echo.
set /p choice="Enter choice [1-2]: "

if "%choice%"=="1" (
    echo.
    echo ==================================
    echo 🔨 Starting in DEVELOPMENT mode...
    echo ==================================
    echo.
    echo Building images...
    docker-compose -f docker-compose.dev.yml build
    echo.
    echo Starting services...
    docker-compose -f docker-compose.dev.yml up -d
    echo.
    echo ✅ Services started!
    echo.
    echo 📊 Service Status:
    docker-compose -f docker-compose.dev.yml ps
    echo.
    echo 🌐 Access URLs:
    echo   - API:        http://localhost:8000
    echo   - Swagger:    http://localhost:8000/api/docs
    echo   - ReDoc:      http://localhost:8000/api/redoc
    echo   - Health:     http://localhost:8000/api/v1/health
    echo   - phpMyAdmin: http://localhost:8080
    echo.
    echo 📝 Useful commands:
    echo   - View logs:      docker-compose -f docker-compose.dev.yml logs -f
    echo   - Stop services:  docker-compose -f docker-compose.dev.yml down
    echo   - Restart:        docker-compose -f docker-compose.dev.yml restart
    echo   - Shell:          docker-compose -f docker-compose.dev.yml exec api bash
    echo.
) else if "%choice%"=="2" (
    echo.
    echo ==================================
    echo 🚀 Starting in PRODUCTION mode...
    echo ==================================
    echo.
    echo Building images...
    docker-compose build
    echo.
    echo Starting services...
    docker-compose up -d
    echo.
    echo ✅ Services started!
    echo.
    echo 📊 Service Status:
    docker-compose ps
    echo.
    echo 🌐 Access URLs:
    echo   - API:     http://localhost:8000
    echo   - Health:  http://localhost:8000/api/v1/health
    echo.
    echo 📝 Useful commands:
    echo   - View logs:      docker-compose logs -f
    echo   - Stop services:  docker-compose down
    echo   - Restart:        docker-compose restart
    echo   - Shell:          docker-compose exec api bash
    echo.
) else (
    echo ❌ Invalid choice. Exiting.
    pause
    exit /b 1
)

echo 🎉 Setup complete! Happy coding!
echo.
pause
