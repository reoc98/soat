# 🏍️ SOAT v2 - Sistema de Intermediación de Seguros

Sistema backend multi-tenant para intermediación de pólizas de seguros SOAT, AP y RCE.

[![FastAPI](https://img.shields.io/badge/FastAPI-0.104.1-009688?style=flat&logo=fastapi)](https://fastapi.tiangolo.com/)
[![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=flat&logo=python)](https://www.python.org/)
[![MySQL](https://img.shields.io/badge/MySQL-8.0-4479A1?style=flat&logo=mysql)](https://www.mysql.com/)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?style=flat&logo=docker)](https://www.docker.com/)
[![AWS](https://img.shields.io/badge/AWS-Integrated-FF9900?style=flat&logo=amazon-aws)](https://aws.amazon.com/)

---

## 📋 Tabla de Contenidos

1. [Características](#-características)
2. [Arquitectura](#-arquitectura)
3. [Inicio Rápido con Docker](#-inicio-rápido-con-docker)
4. [Instalación Manual](#-instalación-manual)
5. [Configuración](#-configuración)
6. [Uso](#-uso)
7. [API Endpoints](#-api-endpoints)
8. [Flujo de Estados](#-flujo-de-estados)
9. [Documentación](#-documentación)
10. [Desarrollo](#-desarrollo)
11. [Testing](#-testing)
12. [Deployment](#-deployment)

---

## ✨ Características

### 🔐 Seguridad y Autenticación
- ✅ Integración con AWS Cognito
- ✅ JWT token validation
- ✅ Role-based access control
- ✅ Multi-tenant architecture

### 🚗 Validación de Propietarios
- ✅ Integración con RUNT (Registro Único Nacional de Tránsito)
- ✅ Validación de propiedad de vehículos
- ✅ Homologaciones automáticas de vehículos
- ✅ Retorno de IDs de homologaciones insertadas

### 💰 Cotización de Seguros
- ✅ SOAT (Seguro Obligatorio de Accidentes de Tránsito)
- ✅ AP (Accidentes Personales)
- ✅ RCE (Responsabilidad Civil Extracontractual)
- ✅ Múltiples aseguradoras integradas
- ✅ Información de productos seleccionados

### 📋 Gestión de Pólizas
- ✅ Pre-expedición de pólizas (cotizador=true)
- ✅ Expedición final (cotizador=false)
- ✅ Selección de planes por producto
- ✅ Estados de sesión con máquina de estados (23 estados)

### 📊 Información de Sesión
- ✅ Servicio de información de sesión con visibilidad condicional
- ✅ Detalles completos en estados pre-cotización
- ✅ Solo metadatos en estados post-cotización
- ✅ Seguimiento de estado en tiempo real

### ☁️ Integración Cloud
- ✅ AWS Secrets Manager para gestión de secretos
- ✅ AWS DynamoDB para logs externos
- ✅ AWS S3 para almacenamiento
- ✅ CloudWatch para métricas

### 🐳 Docker Support
- ✅ Docker Compose para desarrollo y producción
- ✅ Hot-reload en modo desarrollo
- ✅ phpMyAdmin incluido
- ✅ Scripts de inicio rápido

---

## 🏗️ Arquitectura

```
┌─────────────────────────────────────────────────────────────┐
│                      Cliente (Frontend)                      │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                    FastAPI Backend                           │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │   Auth      │  │   Owner     │  │   Quote     │         │
│  │ Middleware  │  │ Validation  │  │  Service    │         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │ Expedition  │  │   Session   │  │   SOAT      │         │
│  │  Service    │  │    Info     │  │   Forms     │         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
└─────────┬───────────────┬───────────────┬───────────────────┘
          │               │               │
          ▼               ▼               ▼
┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│   MySQL     │  │     AWS     │  │  External   │
│  Multi-DB   │  │  Services   │  │    APIs     │
│             │  │             │  │             │
│ • soat_db   │  │ • Cognito   │  │ • RUNT      │
│ • sponsor_1 │  │ • Secrets   │  │ • Mundial   │
│ • sponsor_2 │  │ • DynamoDB  │  │ • Seguros   │
└─────────────┘  └─────────────┘  └─────────────┘
```

### Stack Tecnológico

**Backend:**
- FastAPI 0.104.1
- Python 3.11
- SQLAlchemy 2.0 (Async)
- Pydantic v2 para validación

**Base de Datos:**
- MySQL 8.0
- Alembic para migraciones
- Multi-tenant con esquemas separados

**Cloud:**
- AWS Cognito (Autenticación)
- AWS Secrets Manager (Secretos)
- AWS DynamoDB (Logs)
- AWS S3 (Almacenamiento)

**Herramientas:**
- Docker & Docker Compose
- uvicorn (ASGI server)
- httpx (HTTP client async)

---

## 🚀 Inicio Rápido con Docker

### Prerequisitos
- Docker Desktop instalado
- 4GB+ RAM disponible
- Puertos 3306, 8000, 8080 libres

### 1️⃣ Clonar Repositorio

```bash
git clone <repository-url>
cd soat-v2
```

### 2️⃣ Configurar Variables de Entorno

```bash
# Windows
Copy-Item .env.example .env

# Linux/macOS
cp .env.example .env
```

### 3️⃣ Iniciar con Script

**Windows:**
```cmd
start.bat
```

**Linux/macOS:**
```bash
chmod +x start.sh
./start.sh
```

### 4️⃣ Acceder a los Servicios

- **API:** http://localhost:8000
- **Swagger Docs:** http://localhost:8000/api/docs
- **ReDoc:** http://localhost:8000/api/redoc
- **Health Check:** http://localhost:8000/api/v1/health
- **phpMyAdmin:** http://localhost:8080

**¡Listo!** 🎉

Para más detalles sobre Docker, ver:
- [DOCKER_QUICKSTART.md](DOCKER_QUICKSTART.md) - Inicio rápido
- [DOCKER_SETUP.md](DOCKER_SETUP.md) - Guía completa

---

## 🔧 Instalación Manual

### Prerequisitos
- Python 3.11+
- MySQL 8.0+
- pip y virtualenv

### 1. Crear Entorno Virtual

```bash
# Windows
python -m venv venv
.\venv\Scripts\activate

# Linux/macOS
python3 -m venv venv
source venv/bin/activate
```

### 2. Instalar Dependencias

```bash
pip install -r requirements.txt
```

### 3. Configurar Base de Datos

```sql
CREATE DATABASE soat_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'soat_user'@'localhost' IDENTIFIED BY 'soat_password';
GRANT ALL PRIVILEGES ON soat_db.* TO 'soat_user'@'localhost';
FLUSH PRIVILEGES;
```

### 4. Configurar Variables de Entorno

Crear archivo `.env`:

```env
# Application
APP_NAME=Insurance Intermediary Backend
ENVIRONMENT=dev
LOG_LEVEL=INFO

# Database
DB_HOST=localhost
DB_PORT=3306
DB_USER=soat_user
DB_PASSWORD=soat_password
DB_NAME=soat_db

# AWS (Opcional)
USE_SECRETS_MANAGER=false
USE_COGNITO=false
```

### 5. Ejecutar Migraciones

```bash
alembic upgrade head
```

### 6. Iniciar Servidor

```bash
# Desarrollo con hot-reload
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Producción
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

---

## ⚙️ Configuración

### Variables de Entorno

Ver archivo `.env.example` para todas las opciones disponibles.

#### Configuración Básica

```env
APP_NAME=Insurance Intermediary Backend
APP_VERSION=1.0.0
ENVIRONMENT=dev  # dev, staging, production
DEBUG=false
LOG_LEVEL=INFO   # DEBUG, INFO, WARNING, ERROR
```

#### Base de Datos

```env
DB_HOST=localhost
DB_PORT=3306
DB_USER=soat_user
DB_PASSWORD=soat_password
DB_NAME=soat_db
DB_ECHO=false  # Set to true to see SQL queries
```

#### AWS Services

```env
# Secrets Manager
USE_SECRETS_MANAGER=false
AWS_REGION=us-east-1
AWS_STAGE=dev

# Cognito
USE_COGNITO=false
COGNITO_USER_POOL_ID=us-east-1_xxxxxxxxx
COGNITO_APP_CLIENT_ID=xxxxxxxxxxxxxxxxxx

# Credentials (if not using IAM role)
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
```

#### CORS

```env
ALLOWED_ORIGINS=*  # In production, specify allowed origins
```

---

## 🎯 Uso

### 1. Validación de Propietario

```bash
POST /api/v1/owner-validation/validate
Content-Type: application/json
Authorization: Bearer <token>

{
  "document_type": "CC",
  "document_number": "1234567890",
  "license_plate": "ABC123"
}
```

**Respuesta:**
```json
{
  "session_slug": "550e8400-e29b-41d4-a716-446655440000",
  "session_id": 123,
  "status": "validated",
  "is_owner": true,
  "owner_info": { ... },
  "vehicle_info": {
    "vehicle_id": 456,
    "license_plate": "ABC123",
    "homologations": [
      {
        "id": 1,
        "class_code": "05",
        "class_description": "AUTOMOVIL"
      }
    ]
  }
}
```

### 2. Obtener Información de Sesión

```bash
GET /api/v1/session/info/{session_slug}
Authorization: Bearer <token>
```

**Pre-Cotización (Detalles visibles):**
```json
{
  "session_slug": "550e8400-e29b-41d4-a716-446655440000",
  "status": "validated",
  "can_view_details": true,
  "owner_info": { ... },
  "vehicle_info": { ... }
}
```

**Post-Cotización (Solo metadatos):**
```json
{
  "session_slug": "550e8400-e29b-41d4-a716-446655440000",
  "status": "quoted",
  "can_view_details": false,
  "owner_info": null,
  "vehicle_info": null,
  "message": "Información no disponible en este estado"
}
```

### 3. Crear Cotización

```bash
POST /api/v1/quote/create
Authorization: Bearer <token>

{
  "session_slug": "550e8400-e29b-41d4-a716-446655440000"
}
```

### 4. Ver Productos Cotizados

```bash
GET /api/v1/quote/options/{session_slug}
Authorization: Bearer <token>
```

### 5. Seleccionar Planes

```bash
POST /api/v1/expedition/select-plan/{session_slug}
Authorization: Bearer <token>

{
  "selections": [
    {
      "product_code": "SOAT",
      "selected_option_id": 1
    },
    {
      "product_code": "AP",
      "selected_option_id": 3
    }
  ]
}
```

### 6. Pre-Expedición (Cotizador)

```bash
POST /api/v1/expedition/pre-expedition/{session_slug}
Authorization: Bearer <token>
```

### 7. Expedición Final (Después de Pago)

```bash
POST /api/v1/expedition/expedition/{session_slug}
Authorization: Bearer <token>
```

---

## 📡 API Endpoints

### Autenticación
- `POST /api/v1/auth/login` - Login de usuario

### Validación de Propietario
- `POST /api/v1/owner-validation/validate` - Validar propietario
- `GET /api/v1/owner-validation/status/{slug}` - Estado de validación

### Información de Sesión
- `GET /api/v1/session/info/{slug}` - Información de sesión con visibilidad condicional

### Cotización
- `POST /api/v1/quote/create` - Crear cotización
- `GET /api/v1/quote/options/{slug}` - Ver opciones de productos
- `GET /api/v1/quote/selected/{slug}` - Ver homologación y productos seleccionados
- `GET /api/v1/quote/available/{slug}` - Ver productos disponibles

### Expedición
- `POST /api/v1/expedition/select-plan/{slug}` - Seleccionar planes
- `POST /api/v1/expedition/pre-expedition/{slug}` - Pre-expedición (cotizador=true)
- `POST /api/v1/expedition/expedition/{slug}` - Expedición final (cotizador=false)

### Formularios SOAT
- `GET /api/v1/soat-forms/available` - Formularios disponibles
- `POST /api/v1/soat-forms/assign` - Asignar formulario
- `GET /api/v1/soat-forms/status/{form_number}` - Estado de formulario

### Salud
- `GET /api/v1/health` - Health check

**Documentación Completa:** http://localhost:8000/api/docs

---

## 🔄 Flujo de Estados

```
┌──────────┐
│ CREATED  │ → Sesión creada
└────┬─────┘
     │
     ▼
┌──────────┐
│ STARTED  │ → Sesión iniciada (legacy)
└────┬─────┘
     │
     ▼
┌────────────┐
│ VALIDATING │ → Validando con RUNT
└─────┬──────┘
      │
      ├─→ ┌──────────────────┐
      │   │ VALIDATION_FAILED│ → No es propietario
      │   └──────────────────┘
      │
      ▼
┌───────────┐
│ VALIDATED │ → Propietario confirmado
└─────┬─────┘
      │
      ▼
┌──────────┐
│ QUOTING  │ → Generando cotización
└────┬─────┘
      │
      ▼
┌──────────┐
│ QUOTED   │ → Cotización lista
└────┬─────┘
      │
      ▼
┌─────────────┐
│ SELECTING   │ → Seleccionando planes
└──────┬──────┘
       │
       ▼
┌──────────┐
│ SELECTED │ → Planes seleccionados
└────┬─────┘
      │
      ▼
┌──────────┐
│ ISSUING  │ → Pre-expediendo pólizas
└────┬─────┘
      │
      ▼
┌──────────┐
│ ISSUED   │ → Pre-expedidas (cotizador=true)
└────┬─────┘
      │
      ▼
┌──────────────────┐
│ PAYMENT_PENDING  │ → Esperando pago
└────────┬─────────┘
         │
         ▼
┌───────────────────┐
│ PAYMENT_CONFIRMED │ → Pago confirmado
└─────────┬─────────┘
          │
          ▼
┌───────────┐
│ COMPLETED │ → Pólizas expedidas (cotizador=false)
└───────────┘
```

### Estados Disponibles (23 estados)

| Estado | Descripción |
|--------|-------------|
| `created` | Sesión creada |
| `started` | Sesión iniciada (legacy) |
| `validating` | Validación en curso |
| `validated` | Propietario validado |
| `validation_failed` | Error en validación |
| `quoting` | Generando cotización |
| `quoted` | Cotización generada |
| `quote_expired` | Cotización expirada |
| `selecting` | Seleccionando planes |
| `selected` | Planes seleccionados |
| `issuing` | Emitiendo pólizas |
| `issued` | Pre-expedidas |
| `issuance_failed` | Error en emisión |
| `payment_pending` | Esperando pago |
| `payment_processing` | Procesando pago |
| `payment_confirmed` | Pago confirmado |
| `payment_failed` | Pago rechazado |
| `payment_cancelled` | Pago cancelado |
| `completing` | Completando proceso |
| `completed` | Proceso completado |
| `failed` | Error general |
| `cancelled` | Proceso cancelado |
| `expired` | Sesión expirada |

---

## 📚 Documentación

### Documentación de Servicios

- [SESSION_INFO_SERVICE.md](SESSION_INFO_SERVICE.md) - Servicio de información de sesión
- [EXPEDITION_REFACTORING.md](EXPEDITION_REFACTORING.md) - Servicio de expedición
- [SELECTED_HOMOLOGATION_WITH_QUOTES.md](SELECTED_HOMOLOGATION_WITH_QUOTES.md) - Homologaciones con cotizaciones
- [HOMOLOGATION_ID_UPDATE.md](HOMOLOGATION_ID_UPDATE.md) - Retorno de IDs de homologación
- [QUOTE_SERVICE_README.md](QUOTE_SERVICE_README.md) - Servicio de cotización
- [PRE_EXPEDITION_README.md](PRE_EXPEDITION_README.md) - Pre-expedición
- [SOAT_FORMS_API_REFERENCE.md](SOAT_FORMS_API_REFERENCE.md) - Gestión de formularios

### Docker

- [DOCKER_QUICKSTART.md](DOCKER_QUICKSTART.md) - Inicio rápido con Docker
- [DOCKER_SETUP.md](DOCKER_SETUP.md) - Configuración completa de Docker

### Flows y Estados

- [INSURANCE_SESSION_STATUS_FLOW.md](INSURANCE_SESSION_STATUS_FLOW.md) - Flujo de estados
- [QUOTE_SERVICE_FLOW.md](QUOTE_SERVICE_FLOW.md) - Flujo de cotización

### Base de Datos

- [app/aws/DYNAMODB_SETUP.md](app/aws/DYNAMODB_SETUP.md) - Setup de DynamoDB
- [app/database/README.md](app/database/README.md) - Configuración de base de datos

---

## 🛠️ Desarrollo

### Con Docker (Recomendado)

```bash
# Iniciar entorno de desarrollo
make dev-build
make dev-up
make dev-logs

# Código en app/ se sincroniza automáticamente (hot-reload)

# Ejecutar tests
make dev-test

# Shell en contenedor
make dev-shell

# Detener
make dev-down
```

### Manual

```bash
# Activar entorno virtual
source venv/bin/activate  # Linux/macOS
.\venv\Scripts\activate   # Windows

# Instalar herramientas de desarrollo
pip install pytest pytest-asyncio black flake8 isort mypy

# Ejecutar con hot-reload
uvicorn app.main:app --reload

# Formatear código
black app/
isort app/

# Linting
flake8 app/
mypy app/
```

### Estructura del Proyecto

```
soat-v2/
├── app/
│   ├── api/
│   │   └── v1/
│   │       ├── endpoints/          # Endpoints de la API
│   │       └── routes.py           # Configuración de routers
│   ├── aws/                        # Integraciones AWS
│   ├── core/                       # Configuración y utilidades
│   ├── database/                   # Gestión de base de datos
│   ├── integrations/               # APIs externas
│   ├── middleware/                 # Middleware personalizado
│   ├── models/                     # Modelos SQLAlchemy
│   ├── schemas/                    # Schemas Pydantic
│   ├── services/                   # Lógica de negocio
│   └── main.py                     # Aplicación FastAPI
├── scripts/                        # Scripts de utilidad
├── logs/                           # Logs de aplicación
├── tests/                          # Tests
├── docker-compose.yml              # Docker Compose producción
├── docker-compose.dev.yml          # Docker Compose desarrollo
├── Dockerfile                      # Imagen Docker producción
├── Dockerfile.dev                  # Imagen Docker desarrollo
├── requirements.txt                # Dependencias Python
├── .env.example                    # Template de variables
└── README.md                       # Este archivo
```

---

## 🧪 Testing

### Con Docker

```bash
make dev-test
```

### Manual

```bash
# Ejecutar todos los tests
pytest

# Con coverage
pytest --cov=app --cov-report=html

# Tests específicos
pytest tests/test_owner_validation.py
pytest tests/test_quote.py -v

# Tests con output detallado
pytest -v -s
```

### Escribir Tests

```python
import pytest
from httpx import AsyncClient
from app.main import app

@pytest.mark.asyncio
async def test_health_check():
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/api/v1/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"
```

---

## 🚢 Deployment

### Docker Compose en EC2

```bash
# 1. Conectar a EC2
ssh ubuntu@<ec2-ip>

# 2. Instalar Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# 3. Copiar archivos
scp -r docker-compose.yml .env ubuntu@<ec2-ip>:~/soat-v2/

# 4. Iniciar
cd soat-v2
docker-compose up -d
```

### AWS ECS con ECR

```bash
# 1. Crear repositorio ECR
aws ecr create-repository --repository-name soat-v2-api

# 2. Autenticar Docker
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <account-id>.dkr.ecr.us-east-1.amazonaws.com

# 3. Build y push
docker build -t soat-v2-api .
docker tag soat-v2-api:latest <account-id>.dkr.ecr.us-east-1.amazonaws.com/soat-v2-api:latest
docker push <account-id>.dkr.ecr.us-east-1.amazonaws.com/soat-v2-api:latest

# 4. Crear task definition y service en ECS
```

Ver [DOCKER_SETUP.md](DOCKER_SETUP.md) para más detalles sobre deployment.

---

## 🤝 Contribución

### Git Workflow

```bash
# Crear rama feature
git checkout -b feature/nueva-funcionalidad

# Hacer commits
git add .
git commit -m "feat: agregar nueva funcionalidad"

# Push
git push origin feature/nueva-funcionalidad

# Crear Pull Request en GitHub
```

### Commit Messages

Seguir [Conventional Commits](https://www.conventionalcommits.org/):

- `feat:` Nueva funcionalidad
- `fix:` Corrección de bug
- `docs:` Cambios en documentación
- `style:` Formateo de código
- `refactor:` Refactorización de código
- `test:` Agregar o modificar tests
- `chore:` Tareas de mantenimiento

---

## 📄 Licencia

[Especificar licencia del proyecto]

---

## 👥 Equipo

[Información del equipo]

---

## 📞 Soporte

Para preguntas o problemas:
- **Issues:** [GitHub Issues](link-a-issues)
- **Email:** soporte@ejemplo.com
- **Documentación:** Ver archivos `*_README.md` y `*_GUIDE.md`

---

## 🔗 Links Útiles

- **FastAPI Docs:** https://fastapi.tiangolo.com/
- **SQLAlchemy:** https://docs.sqlalchemy.org/
- **Pydantic:** https://docs.pydantic.dev/
- **Docker:** https://docs.docker.com/
- **AWS SDK:** https://boto3.amazonaws.com/v1/documentation/api/latest/index.html

---

**Fecha de última actualización:** 2025-10-18  
**Versión:** 1.0.0