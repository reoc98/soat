# 📦 Archivos Docker Creados - Resumen

Este documento lista todos los archivos Docker creados para el proyecto SOAT v2.

---

## 📁 Archivos Creados

### 1. Configuración Docker

| Archivo | Descripción | Uso |
|---------|-------------|-----|
| `Dockerfile` | Imagen optimizada para producción | `docker build -f Dockerfile .` |
| `Dockerfile.dev` | Imagen de desarrollo con hot-reload | `docker build -f Dockerfile.dev .` |
| `docker-compose.yml` | Orquestación para producción | `docker-compose up -d` |
| `docker-compose.dev.yml` | Orquestación para desarrollo | `docker-compose -f docker-compose.dev.yml up -d` |
| `.dockerignore` | Archivos a ignorar en build | Automático en build |
| `.env.example` | Template de variables de entorno | `cp .env.example .env` |

### 2. Scripts de Inicio

| Archivo | Descripción | Plataforma |
|---------|-------------|------------|
| `start.bat` | Script de inicio rápido | Windows |
| `start.sh` | Script de inicio rápido | Linux/macOS |
| `Makefile` | Comandos simplificados | Todos (requiere make) |

### 3. Documentación

| Archivo | Contenido | Para quién |
|---------|-----------|------------|
| `DOCKER_SETUP.md` | Guía completa de Docker | Todos los niveles |
| `DOCKER_QUICKSTART.md` | Inicio rápido (5 min) | Principiantes |
| `INSTALLATION_CHECKLIST.md` | Checklist de instalación | Verificación paso a paso |
| `DOCKER_FILES_SUMMARY.md` | Este archivo | Referencia rápida |

---

## 🚀 Guía de Uso Rápido

### Primera Vez (Setup Inicial)

```bash
# 1. Copiar variables de entorno
cp .env.example .env

# 2. Editar .env con tu configuración
nano .env  # o usar tu editor favorito

# 3. Iniciar con script
# Windows:
start.bat

# Linux/macOS:
chmod +x start.sh
./start.sh
```

### Desarrollo Diario

**Con Makefile (Recomendado):**
```bash
make dev-up      # Iniciar
make dev-logs    # Ver logs
make dev-shell   # Entrar al contenedor
make dev-down    # Detener
```

**Sin Makefile:**
```bash
docker-compose -f docker-compose.dev.yml up -d
docker-compose -f docker-compose.dev.yml logs -f
docker-compose -f docker-compose.dev.yml exec api bash
docker-compose -f docker-compose.dev.yml down
```

### Producción

**Con Makefile:**
```bash
make build    # Construir
make up       # Iniciar
make logs     # Ver logs
make down     # Detener
```

**Sin Makefile:**
```bash
docker-compose build
docker-compose up -d
docker-compose logs -f
docker-compose down
```

---

## 📋 Descripción Detallada de Archivos

### `Dockerfile` (Producción)

**Características:**
- Base: `python:3.11-slim`
- Optimizado para tamaño reducido
- Sin herramientas de desarrollo
- Incluye healthcheck
- Multi-stage build compatible

**Uso:**
```bash
docker build -t soat-v2-api:latest .
docker run -p 8000:8000 --env-file .env soat-v2-api:latest
```

**Puertos expuestos:**
- `8000` - API FastAPI

---

### `Dockerfile.dev` (Desarrollo)

**Características:**
- Base: `python:3.11-slim`
- Incluye herramientas de desarrollo:
  - pytest, pytest-asyncio, pytest-cov
  - black, flake8, isort, mypy
  - git
- Hot-reload habilitado
- Volúmenes montados para sincronización

**Uso:**
```bash
docker build -f Dockerfile.dev -t soat-v2-api:dev .
docker run -v $(pwd)/app:/app/app -p 8000:8000 soat-v2-api:dev
```

---

### `docker-compose.yml` (Producción)

**Servicios:**

#### 1. MySQL Database (`mysql`)
- Imagen: `mysql:8.0`
- Puerto: `3306`
- Volumen: `mysql_data` (persistente)
- Healthcheck: `mysqladmin ping`
- Variables configurables en `.env`

#### 2. FastAPI API (`api`)
- Build desde `Dockerfile`
- Puerto: `8000`
- Depende de: `mysql` (healthy)
- Healthcheck: `curl /api/v1/health`
- Volumen de logs montado

#### 3. phpMyAdmin (`phpmyadmin`)
- Imagen: `phpmyadmin:latest`
- Puerto: `8080`
- Profile: `debug` (opcional)
- Solo inicia con: `docker-compose --profile debug up`

**Red:**
- `soat_network` (bridge)

**Volúmenes:**
- `mysql_data` - Persistencia de base de datos
- `./logs` - Logs de aplicación

---

### `docker-compose.dev.yml` (Desarrollo)

**Diferencias con Producción:**

1. **API Container:**
   - Build desde `Dockerfile.dev`
   - Volúmenes montados:
     - `./app:/app/app` - Hot-reload de código
     - `./scripts:/app/scripts`
     - `./tests:/app/tests`
   - Comando: `uvicorn --reload --log-level debug`
   - Variables de entorno en modo DEBUG

2. **phpMyAdmin:**
   - Siempre activo (sin profile)

3. **Volúmenes:**
   - `mysql_dev_data` (separado de producción)

4. **Red:**
   - `soat_network_dev` (separada)

---

### `.dockerignore`

**Archivos/carpetas excluidos del build:**
- Python: `__pycache__`, `*.pyc`, `venv/`
- IDEs: `.vscode/`, `.idea/`
- Git: `.git/`, `.gitignore`
- Environment: `.env`, `.env.local`
- Logs: `logs/`, `*.log`
- Testing: `.pytest_cache/`, `.coverage`
- Documentation: `*.md` (excepto README.md)
- Docker: `Dockerfile`, `docker-compose.yml`

**Beneficios:**
- Builds más rápidos
- Imágenes más pequeñas
- No incluye archivos sensibles

---

### `.env.example`

**Secciones:**

1. **Application:**
   - APP_NAME, APP_VERSION, ENVIRONMENT
   - DEBUG, LOG_LEVEL, DB_ECHO

2. **Docker Configuration:**
   - API_PORT, MYSQL_PORT, PHPMYADMIN_PORT

3. **Database Connection:**
   - DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME
   - MYSQL_ROOT_PASSWORD, MYSQL_DATABASE, MYSQL_USER, MYSQL_PASSWORD

4. **AWS Configuration:**
   - USE_SECRETS_MANAGER, AWS_REGION, AWS_STAGE
   - AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY
   - USE_COGNITO, COGNITO_USER_POOL_ID, COGNITO_APP_CLIENT_ID

5. **CORS:**
   - ALLOWED_ORIGINS

**Uso:**
```bash
# Copiar y editar
cp .env.example .env
nano .env
```

**⚠️ IMPORTANTE:** Nunca commitear `.env` al repositorio.

---

### `start.bat` (Windows)

**Funcionalidad:**
1. Verifica instalación de Docker
2. Crea `.env` si no existe
3. Pregunta modo: Development (1) o Production (2)
4. Construye imágenes
5. Inicia servicios
6. Muestra URLs de acceso
7. Lista comandos útiles

**Uso:**
```cmd
start.bat
```

Luego elegir opción con número.

---

### `start.sh` (Linux/macOS)

**Funcionalidad:**
Igual que `start.bat` pero para Unix/Linux.

**Uso:**
```bash
chmod +x start.sh
./start.sh
```

**Prerequisitos:**
- Docker instalado
- Docker Compose instalado
- Bash shell

---

### `Makefile`

**Comandos disponibles:**

#### Producción
```bash
make help        # Mostrar ayuda
make build       # Construir imágenes
make up          # Iniciar servicios
make down        # Detener servicios
make restart     # Reiniciar servicios
make logs        # Ver todos los logs
make logs-api    # Ver logs de API
make logs-db     # Ver logs de MySQL
make shell       # Shell en API container
make shell-db    # MySQL shell
make test        # Ejecutar tests
make clean       # Limpiar todo (⚠️ destructivo)
make ps          # Ver estado de servicios
```

#### Desarrollo
```bash
make dev-build       # Construir imagen dev
make dev-up          # Iniciar con hot-reload
make dev-down        # Detener
make dev-restart     # Reiniciar
make dev-logs        # Ver logs
make dev-logs-api    # Ver logs API
make dev-shell       # Shell en contenedor
make dev-shell-db    # MySQL shell
make dev-test        # Ejecutar tests
make dev-clean       # Limpiar todo dev
make ps-dev          # Ver estado
```

#### Base de Datos
```bash
make db-migrate              # Ejecutar migraciones
make db-revision msg="desc"  # Crear migración
```

#### Utilidades
```bash
make prune       # Limpiar sistema Docker
```

**Prerequisitos:**
- GNU Make instalado
  - Linux/macOS: Generalmente incluido
  - Windows: Instalar con Chocolatey o Git Bash

---

## 🌐 Puertos Usados

| Servicio | Puerto Host | Puerto Container | Descripción |
|----------|-------------|------------------|-------------|
| API | 8000 | 8000 | FastAPI Backend |
| MySQL | 3306 | 3306 | Base de datos |
| phpMyAdmin | 8080 | 80 | Administrador BD |

**Configurables en `.env`:**
```env
API_PORT=8000
MYSQL_PORT=3306
PHPMYADMIN_PORT=8080
```

---

## 📦 Volúmenes Docker

### Producción

| Volumen | Tipo | Montaje | Propósito |
|---------|------|---------|-----------|
| `mysql_data` | Named | `/var/lib/mysql` | Persistencia de MySQL |
| `./logs` | Bind | `/app/logs` | Logs de aplicación |

### Desarrollo (adicional)

| Volumen | Tipo | Montaje | Propósito |
|---------|------|---------|-----------|
| `mysql_dev_data` | Named | `/var/lib/mysql` | BD de desarrollo |
| `./app` | Bind | `/app/app` | Hot-reload de código |
| `./scripts` | Bind | `/app/scripts` | Scripts de utilidad |
| `./tests` | Bind | `/app/tests` | Tests |

**Gestión:**
```bash
# Listar volúmenes
docker volume ls

# Inspeccionar volumen
docker volume inspect soat-v2_mysql_data

# Eliminar volumen (⚠️ elimina datos)
docker volume rm soat-v2_mysql_data

# Eliminar todos los volúmenes sin usar
docker volume prune
```

---

## 🔍 Health Checks

### API Health Check

**Configuración:**
```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8000/api/v1/health"]
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 40s
```

**Verificar:**
```bash
docker inspect soat_api | grep -A 10 Health

# o
curl http://localhost:8000/api/v1/health
```

### MySQL Health Check

**Configuración:**
```yaml
healthcheck:
  test: ["CMD", "mysqladmin", "ping", "-h", "localhost"]
  interval: 10s
  timeout: 5s
  retries: 5
```

**Verificar:**
```bash
docker inspect soat_mysql | grep -A 10 Health
```

---

## 🐛 Troubleshooting Común

### Puerto ya en uso

**Error:**
```
Bind for 0.0.0.0:8000 failed: port is already allocated
```

**Solución:**
Cambiar puerto en `.env`:
```env
API_PORT=8001
```

### Contenedor no inicia

**Ver logs:**
```bash
docker-compose logs <servicio>
```

**Reconstruir:**
```bash
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

### Base de datos corrupta

**Recrear volumen:**
```bash
docker-compose down -v
docker volume rm soat-v2_mysql_data
docker-compose up -d
```

### Cambios no se reflejan (desarrollo)

**Verificar volúmenes:**
```bash
docker inspect soat_api_dev | grep -A 20 Mounts
```

**Reiniciar:**
```bash
docker-compose -f docker-compose.dev.yml restart api
```

---

## 📚 Documentación Relacionada

| Documento | Descripción | Cuando Usar |
|-----------|-------------|-------------|
| [DOCKER_QUICKSTART.md](DOCKER_QUICKSTART.md) | Guía de 5 minutos | Primera vez, inicio rápido |
| [DOCKER_SETUP.md](DOCKER_SETUP.md) | Guía completa | Configuración avanzada, troubleshooting |
| [INSTALLATION_CHECKLIST.md](INSTALLATION_CHECKLIST.md) | Checklist paso a paso | Verificar instalación |
| [README.md](README.md) | Documentación principal | Información general del proyecto |

---

## 🔄 Flujo de Trabajo Recomendado

### Desarrollo Local

```bash
# 1. Primera vez
cp .env.example .env
nano .env  # Editar configuración

# 2. Iniciar
make dev-build
make dev-up

# 3. Desarrollar
# Editar archivos en app/
# Los cambios se reflejan automáticamente

# 4. Ver logs en tiempo real
make dev-logs-api

# 5. Tests
make dev-test

# 6. Al finalizar
make dev-down
```

### Testing/Staging

```bash
# 1. Configurar .env para staging
ENVIRONMENT=staging

# 2. Construir y desplegar
make build
make up

# 3. Verificar
make logs
curl http://localhost:8000/api/v1/health

# 4. Si todo OK, proceder a producción
```

### Producción

```bash
# 1. Configurar .env para producción
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO
USE_SECRETS_MANAGER=true

# 2. Construir optimizado
docker build --no-cache -t soat-v2-api:prod .

# 3. Tag y push a registry
docker tag soat-v2-api:prod registry/soat-v2-api:latest
docker push registry/soat-v2-api:latest

# 4. Desplegar en servidor
# Ver DOCKER_SETUP.md para deployment en AWS
```

---

## ✅ Checklist de Archivos

Verifica que tengas todos estos archivos:

- [ ] `Dockerfile`
- [ ] `Dockerfile.dev`
- [ ] `docker-compose.yml`
- [ ] `docker-compose.dev.yml`
- [ ] `.dockerignore`
- [ ] `.env.example`
- [ ] `start.bat`
- [ ] `start.sh`
- [ ] `Makefile`
- [ ] `DOCKER_SETUP.md`
- [ ] `DOCKER_QUICKSTART.md`
- [ ] `INSTALLATION_CHECKLIST.md`
- [ ] `DOCKER_FILES_SUMMARY.md` (este archivo)
- [ ] `.env` (creado por ti, NO en git)

---

## 🎯 Próximos Pasos

1. **Si es tu primera vez:**
   - Leer [DOCKER_QUICKSTART.md](DOCKER_QUICKSTART.md)
   - Ejecutar `start.bat` o `start.sh`
   - Seguir [INSTALLATION_CHECKLIST.md](INSTALLATION_CHECKLIST.md)

2. **Para desarrollo:**
   - Leer [DOCKER_SETUP.md](DOCKER_SETUP.md) sección "Desarrollo"
   - Usar `make dev-*` commands
   - Configurar IDE

3. **Para producción:**
   - Leer [DOCKER_SETUP.md](DOCKER_SETUP.md) sección "Deployment"
   - Configurar AWS Secrets Manager
   - Configurar CI/CD

---

**Fecha de creación:** 2025-10-18  
**Versión:** 1.0  
**Última actualización:** 2025-10-18
