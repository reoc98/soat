# 🐳 Docker Setup - SOAT v2

Guía completa para ejecutar el proyecto **SOAT v2** con Docker y Docker Compose.

---

## 📋 Tabla de Contenidos

1. [Requisitos Previos](#requisitos-previos)
2. [Estructura de Archivos Docker](#estructura-de-archivos-docker)
3. [Configuración Inicial](#configuración-inicial)
4. [Ejecución en Producción](#ejecución-en-producción)
5. [Ejecución en Desarrollo](#ejecución-en-desarrollo)
6. [Comandos Útiles](#comandos-útiles)
7. [Acceso a Servicios](#acceso-a-servicios)
8. [Troubleshooting](#troubleshooting)
9. [Mejores Prácticas](#mejores-prácticas)

---

## 🔧 Requisitos Previos

### Instalación de Docker

#### Windows
1. Descargar [Docker Desktop para Windows](https://www.docker.com/products/docker-desktop)
2. Ejecutar instalador
3. Reiniciar sistema
4. Verificar instalación:
```powershell
docker --version
docker-compose --version
```

#### Linux (Ubuntu/Debian)
```bash
# Actualizar paquetes
sudo apt-get update

# Instalar Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Agregar usuario al grupo docker
sudo usermod -aG docker $USER

# Instalar Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Verificar instalación
docker --version
docker-compose --version
```

#### macOS
1. Descargar [Docker Desktop para Mac](https://www.docker.com/products/docker-desktop)
2. Arrastrar a Applications
3. Ejecutar Docker Desktop
4. Verificar instalación:
```bash
docker --version
docker-compose --version
```

### Requisitos de Sistema
- **RAM:** Mínimo 4GB, recomendado 8GB
- **Disco:** Mínimo 10GB libres
- **CPU:** 2+ cores recomendado

---

## 📁 Estructura de Archivos Docker

```
soat-v2/
├── Dockerfile                  # Imagen de producción
├── Dockerfile.dev             # Imagen de desarrollo con hot-reload
├── docker-compose.yml         # Configuración de producción
├── docker-compose.dev.yml     # Configuración de desarrollo
├── .dockerignore              # Archivos a ignorar en build
├── .env.example               # Template de variables de entorno
├── .env                       # Variables de entorno (crear desde .env.example)
├── Makefile                   # Comandos simplificados
└── DOCKER_SETUP.md            # Esta guía
```

### Archivos Creados

#### 1. `Dockerfile` (Producción)
- Imagen optimizada para producción
- Python 3.11 slim
- Sin hot-reload
- Healthcheck incluido

#### 2. `Dockerfile.dev` (Desarrollo)
- Incluye herramientas de desarrollo
- Hot-reload habilitado
- Debugging tools

#### 3. `docker-compose.yml` (Producción)
```yaml
Servicios:
- mysql:        Base de datos MySQL 8.0
- api:          API FastAPI
- phpmyadmin:   Administrador BD (opcional)
```

#### 4. `docker-compose.dev.yml` (Desarrollo)
```yaml
Servicios:
- mysql:        BD con volumen persistente dev
- api:          API con hot-reload y debug
- phpmyadmin:   Siempre activo en desarrollo
```

---

## ⚙️ Configuración Inicial

### 1. Crear Archivo .env

Copiar el archivo de ejemplo:

**Windows (PowerShell):**
```powershell
Copy-Item .env.example .env
```

**Linux/macOS:**
```bash
cp .env.example .env
```

### 2. Editar Variables de Entorno

Abrir `.env` y configurar según necesidad:

```env
# ============================================
# CONFIGURACIÓN BÁSICA
# ============================================
APP_NAME=Insurance Intermediary Backend
ENVIRONMENT=dev
LOG_LEVEL=INFO

# ============================================
# PUERTOS
# ============================================
API_PORT=8000           # Puerto de la API
MYSQL_PORT=3306         # Puerto de MySQL
PHPMYADMIN_PORT=8080    # Puerto de phpMyAdmin

# ============================================
# BASE DE DATOS
# ============================================
MYSQL_ROOT_PASSWORD=rootpassword
MYSQL_DATABASE=soat_db
MYSQL_USER=soat_user
MYSQL_PASSWORD=soat_password

DB_HOST=mysql           # Usar 'mysql' para Docker
DB_PORT=3306
DB_USER=soat_user
DB_PASSWORD=soat_password
DB_NAME=soat_db

# ============================================
# AWS (Opcional)
# ============================================
USE_SECRETS_MANAGER=false
AWS_REGION=us-east-1
USE_COGNITO=false
```

### 3. Configuración de AWS (Opcional)

Si vas a usar AWS Secrets Manager o Cognito:

```env
# Secrets Manager
USE_SECRETS_MANAGER=true
AWS_REGION=us-east-1
AWS_STAGE=dev
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key

# Cognito
USE_COGNITO=true
COGNITO_USER_POOL_ID=us-east-1_xxxxxxxxx
COGNITO_APP_CLIENT_ID=xxxxxxxxxxxxxxxxxx
```

---

## 🚀 Ejecución en Producción

### Opción 1: Usar Makefile (Recomendado)

**Ver comandos disponibles:**
```bash
make help
```

**Iniciar servicios:**
```bash
make build    # Construir imágenes
make up       # Iniciar servicios
make logs     # Ver logs
```

**Detener servicios:**
```bash
make down
```

### Opción 2: Docker Compose Directo

**Construir imágenes:**
```bash
docker-compose build
```

**Iniciar servicios:**
```bash
docker-compose up -d
```

**Ver logs:**
```bash
docker-compose logs -f
```

**Ver logs solo de API:**
```bash
docker-compose logs -f api
```

**Detener servicios:**
```bash
docker-compose down
```

**Detener y eliminar volúmenes:**
```bash
docker-compose down -v
```

---

## 🔨 Ejecución en Desarrollo

### Características del Modo Desarrollo

✅ **Hot-reload:** Cambios en código se reflejan automáticamente  
✅ **Debug mode:** Logs detallados y traceback completo  
✅ **Tools incluidas:** pytest, black, flake8, mypy  
✅ **phpMyAdmin:** Siempre activo para gestionar BD  
✅ **Volúmenes montados:** Código sincronizado con container

### Opción 1: Usar Makefile (Recomendado)

**Iniciar desarrollo:**
```bash
make dev-build    # Construir imagen dev
make dev-up       # Iniciar con hot-reload
make dev-logs     # Ver logs
```

**Shell en contenedor:**
```bash
make dev-shell    # Bash en API container
```

**Ejecutar tests:**
```bash
make dev-test
```

**Detener desarrollo:**
```bash
make dev-down
```

### Opción 2: Docker Compose Directo

**Iniciar:**
```bash
docker-compose -f docker-compose.dev.yml build
docker-compose -f docker-compose.dev.yml up -d
docker-compose -f docker-compose.dev.yml logs -f
```

**Detener:**
```bash
docker-compose -f docker-compose.dev.yml down
```

---

## 💡 Comandos Útiles

### Makefile Commands

```bash
# PRODUCCIÓN
make build          # Construir imágenes
make up             # Iniciar servicios
make down           # Detener servicios
make restart        # Reiniciar servicios
make logs           # Ver todos los logs
make logs-api       # Ver logs de API
make logs-db        # Ver logs de MySQL
make shell          # Shell en API container
make shell-db       # MySQL shell
make test           # Ejecutar tests
make clean          # Limpiar todo (⚠️ destructivo)
make ps             # Ver estado de servicios

# DESARROLLO
make dev-build      # Construir imagen dev
make dev-up         # Iniciar con hot-reload
make dev-down       # Detener
make dev-logs       # Ver logs
make dev-shell      # Shell en API container
make dev-test       # Ejecutar tests
make ps-dev         # Ver estado

# BASE DE DATOS
make db-migrate     # Ejecutar migraciones
make db-revision msg="descripción"  # Crear migración
```

### Docker Compose Commands

```bash
# Ver servicios en ejecución
docker-compose ps

# Ver logs específicos
docker-compose logs -f api
docker-compose logs -f mysql
docker-compose logs --tail=100 api

# Reiniciar servicio específico
docker-compose restart api

# Reconstruir un servicio
docker-compose build api
docker-compose up -d --no-deps --build api

# Ejecutar comando en contenedor
docker-compose exec api python --version
docker-compose exec api pip list

# Ver uso de recursos
docker stats

# Limpiar containers detenidos
docker container prune

# Limpiar imágenes no usadas
docker image prune -a

# Limpiar todo (⚠️ peligroso)
docker system prune -af --volumes
```

---

## 🌐 Acceso a Servicios

### API FastAPI

**URL:** http://localhost:8000

**Endpoints importantes:**
- **Documentación Swagger:** http://localhost:8000/api/docs
- **Documentación ReDoc:** http://localhost:8000/api/redoc
- **OpenAPI JSON:** http://localhost:8000/api/openapi.json
- **Health Check:** http://localhost:8000/api/v1/health

**Ejemplo de uso:**
```bash
# Health check
curl http://localhost:8000/api/v1/health

# Con autenticación
curl -H "Authorization: Bearer <token>" http://localhost:8000/api/v1/session/info/abc123
```

### phpMyAdmin

**URL:** http://localhost:8080

**Credenciales por defecto:**
- **Usuario:** `soat_user` (o valor en `.env`)
- **Contraseña:** `soat_password` (o valor en `.env`)

**Características:**
- Explorar tablas
- Ejecutar queries SQL
- Importar/exportar datos
- Gestionar usuarios

### MySQL Directo

**Desde host (si puerto 3306 expuesto):**
```bash
mysql -h localhost -P 3306 -u soat_user -p
# Ingresar password: soat_password
```

**Desde contenedor API:**
```bash
make shell
mysql -h mysql -u soat_user -p
```

**Desde MySQL container:**
```bash
docker-compose exec mysql mysql -u soat_user -p
```

---

## 🐛 Troubleshooting

### Problema 1: Puerto ya en uso

**Error:**
```
ERROR: for api  Cannot start service api: Ports are not available: 
listen tcp 0.0.0.0:8000: bind: address already in use
```

**Solución:**

**Windows (PowerShell):**
```powershell
# Ver qué proceso usa el puerto
netstat -ano | findstr :8000

# Matar proceso (reemplazar PID)
taskkill /PID <PID> /F

# O cambiar puerto en .env
# API_PORT=8001
```

**Linux/macOS:**
```bash
# Ver qué proceso usa el puerto
lsof -i :8000

# Matar proceso
kill -9 <PID>

# O cambiar puerto en .env
```

### Problema 2: Contenedor no inicia

**Ver logs completos:**
```bash
docker-compose logs api
```

**Revisar healthcheck:**
```bash
docker inspect soat_api | grep -A 10 Health
```

**Entrar al contenedor (si está corriendo):**
```bash
docker-compose exec api bash
```

**Reconstruir desde cero:**
```bash
make clean
make build
make up
```

### Problema 3: Base de datos no conecta

**Verificar que MySQL esté healthy:**
```bash
docker-compose ps
```

Debe mostrar `healthy` en la columna Status.

**Ver logs de MySQL:**
```bash
make logs-db
```

**Verificar conexión desde API:**
```bash
make shell
# Dentro del container:
ping mysql
nc -zv mysql 3306
```

**Recrear volumen de MySQL:**
```bash
docker-compose down -v
docker volume rm soat-v2_mysql_data
make up
```

### Problema 4: Cambios en código no se reflejan

**Modo Producción:**
Los cambios NO se reflejan automáticamente. Debes reconstruir:
```bash
make down
make build
make up
```

**Modo Desarrollo:**
Los cambios SÍ deben reflejarse automátamente. Si no:
```bash
make dev-restart
```

**Verificar que volúmenes estén montados:**
```bash
docker-compose -f docker-compose.dev.yml ps
docker inspect soat_api_dev | grep -A 20 Mounts
```

### Problema 5: Error de permisos en logs/

**Error:**
```
PermissionError: [Errno 13] Permission denied: '/app/logs/app.log'
```

**Solución:**

**Linux/macOS:**
```bash
sudo chmod -R 777 logs/
```

**Windows:**
Click derecho en carpeta `logs` → Propiedades → Seguridad → Editar → Permitir control total

**O recrear en Dockerfile:**
```dockerfile
RUN mkdir -p /app/logs && chmod 777 /app/logs
```

### Problema 6: Out of Memory

**Síntomas:**
- Contenedores se detienen aleatoriamente
- Error: `OOMKilled`

**Solución:**

Aumentar memoria en Docker Desktop:
- **Windows/macOS:** Settings → Resources → Memory → 4GB+

Limitar recursos en `docker-compose.yml`:
```yaml
services:
  api:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
```

### Problema 7: Secrets Manager no funciona

**Verificar credenciales AWS:**
```bash
make shell
# Dentro del container:
aws sts get-caller-identity
```

**Verificar variables:**
```bash
docker-compose exec api env | grep AWS
```

**Testing sin AWS:**
```env
USE_SECRETS_MANAGER=false
USE_COGNITO=false
```

---

## 🎯 Mejores Prácticas

### 1. Desarrollo Local

✅ **DO:**
- Usar `docker-compose.dev.yml` para desarrollo
- Montar código como volumen para hot-reload
- Usar logs en modo DEBUG
- Mantener phpMyAdmin activo

❌ **DON'T:**
- No usar producción para desarrollo
- No hardcodear credenciales en código
- No commitear `.env` al repositorio

### 2. Producción

✅ **DO:**
- Usar `docker-compose.yml` estándar
- Configurar healthchecks
- Usar secrets manager en AWS
- Limitar recursos por servicio
- Hacer backup de volúmenes regularmente

❌ **DON'T:**
- No exponer puertos innecesarios
- No usar credenciales por defecto
- No deshabilitar healthchecks

### 3. Seguridad

✅ **DO:**
```bash
# Rotar secrets regularmente
# Usar least privilege en IAM
# Escanear imágenes por vulnerabilidades
docker scan soat-v2_api

# Actualizar imágenes base
docker pull python:3.11-slim
make build
```

❌ **DON'T:**
```bash
# No correr como root
# No exponer MySQL en producción (quitar ports:)
# No usar :latest en producción
```

### 4. Performance

**Optimizar builds:**
```dockerfile
# Layer caching: requirements primero
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY ./app ./app  # Después el código
```

**Multi-stage builds:**
```dockerfile
FROM python:3.11-slim as builder
# ... build dependencies
FROM python:3.11-slim
# ... copy only artifacts
```

**Health checks ligeros:**
```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8000/api/v1/health"]
  interval: 30s  # No muy frecuente
  timeout: 10s
  retries: 3
```

### 5. Gestión de Volúmenes

**Backup de base de datos:**
```bash
# Exportar
docker-compose exec mysql mysqldump -u soat_user -p soat_db > backup.sql

# Importar
docker-compose exec -T mysql mysql -u soat_user -p soat_db < backup.sql
```

**Listar volúmenes:**
```bash
docker volume ls
```

**Inspeccionar volumen:**
```bash
docker volume inspect soat-v2_mysql_data
```

**Backup de volumen:**
```bash
docker run --rm -v soat-v2_mysql_data:/data -v $(pwd):/backup ubuntu tar czf /backup/mysql_backup.tar.gz /data
```

---

## 🚀 Deployment en AWS

### Usando ECS con ECR

**1. Crear repositorio ECR:**
```bash
aws ecr create-repository --repository-name soat-v2-api --region us-east-1
```

**2. Autenticar Docker:**
```bash
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <account-id>.dkr.ecr.us-east-1.amazonaws.com
```

**3. Tag y push:**
```bash
docker tag soat-v2_api:latest <account-id>.dkr.ecr.us-east-1.amazonaws.com/soat-v2-api:latest
docker push <account-id>.dkr.ecr.us-east-1.amazonaws.com/soat-v2-api:latest
```

**4. Crear task definition ECS:**
```json
{
  "family": "soat-v2-api",
  "containerDefinitions": [{
    "name": "api",
    "image": "<account-id>.dkr.ecr.us-east-1.amazonaws.com/soat-v2-api:latest",
    "cpu": 512,
    "memory": 1024,
    "portMappings": [{
      "containerPort": 8000,
      "protocol": "tcp"
    }],
    "environment": [
      {"name": "USE_SECRETS_MANAGER", "value": "true"},
      {"name": "AWS_REGION", "value": "us-east-1"}
    ]
  }]
}
```

### Usando Docker Compose en EC2

**1. Instalar Docker en EC2:**
```bash
ssh ubuntu@<ec2-ip>
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker ubuntu
```

**2. Copiar archivos:**
```bash
scp -r docker-compose.yml .env ubuntu@<ec2-ip>:~/soat-v2/
```

**3. Ejecutar:**
```bash
ssh ubuntu@<ec2-ip>
cd soat-v2
docker-compose up -d
```

---

## 📊 Monitoreo

### Ver recursos en tiempo real

```bash
# Todos los servicios
docker stats

# Solo API
docker stats soat_api

# Formato personalizado
docker stats --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}"
```

### Logs estructurados

```bash
# Últimas 100 líneas
docker-compose logs --tail=100 api

# Seguir logs en tiempo real
docker-compose logs -f api

# Filtrar por palabra
docker-compose logs api | grep ERROR

# Con timestamps
docker-compose logs -t api
```

### Inspeccionar contenedor

```bash
# Info completa
docker inspect soat_api

# IP del contenedor
docker inspect soat_api | grep IPAddress

# Healthcheck status
docker inspect soat_api | grep -A 10 Health
```

---

## 🔄 CI/CD con GitHub Actions

Ejemplo de workflow:

```yaml
name: Build and Push

on:
  push:
    branches: [main]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      
      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v1
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: us-east-1
      
      - name: Login to ECR
        run: |
          aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin ${{ secrets.ECR_REGISTRY }}
      
      - name: Build and push
        run: |
          docker build -t soat-v2-api .
          docker tag soat-v2-api:latest ${{ secrets.ECR_REGISTRY }}/soat-v2-api:latest
          docker push ${{ secrets.ECR_REGISTRY }}/soat-v2-api:latest
```

---

## 📝 Checklist de Setup

### Setup Inicial
- [ ] Docker y Docker Compose instalados
- [ ] Repositorio clonado
- [ ] Archivo `.env` creado y configurado
- [ ] Puertos 3306, 8000, 8080 disponibles

### Primera Ejecución
- [ ] `make build` exitoso
- [ ] `make up` levanta servicios
- [ ] API responde en http://localhost:8000/api/v1/health
- [ ] Swagger docs accesibles en http://localhost:8000/api/docs
- [ ] phpMyAdmin accesible en http://localhost:8080
- [ ] MySQL acepta conexiones

### Desarrollo
- [ ] `make dev-build` exitoso
- [ ] `make dev-up` levanta con hot-reload
- [ ] Cambios en código se reflejan automáticamente
- [ ] Tests corren con `make dev-test`

### Producción
- [ ] Variables de entorno configuradas para producción
- [ ] Secrets Manager habilitado (si aplica)
- [ ] Healthchecks funcionando
- [ ] Logs en nivel apropiado (INFO/WARNING)

---

## 🆘 Soporte

### Recursos Útiles

- **Docker Docs:** https://docs.docker.com/
- **Docker Compose:** https://docs.docker.com/compose/
- **FastAPI:** https://fastapi.tiangolo.com/
- **MySQL:** https://dev.mysql.com/doc/

### Comandos de Diagnóstico

```bash
# Sistema Docker
docker version
docker info
docker system df  # Uso de disco

# Servicios
make ps
docker-compose ps

# Logs completos
make logs > logs_dump.txt

# Recursos
docker stats --no-stream > stats.txt

# Inspección
docker inspect soat_api > inspect_api.json
docker inspect soat_mysql > inspect_mysql.json
```

---

**Fecha:** 2025-10-18  
**Versión:** 1.0  
**Autor:** Sistema SOAT v2  
**Última actualización:** 2025-10-18
