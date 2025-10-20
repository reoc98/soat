# 🚀 Comandos Docker - Referencia Rápida

Cheat sheet de comandos Docker para el proyecto SOAT v2.

---

## 🏃 Inicio Rápido

### Primera Vez
```bash
# Windows
start.bat

# Linux/macOS
chmod +x start.sh && ./start.sh
```

### Con Makefile
```bash
# Desarrollo
make dev-up      # Iniciar
make dev-down    # Detener

# Producción
make up          # Iniciar
make down        # Detener
```

---

## 🔨 Desarrollo

### Iniciar/Detener
```bash
# Iniciar
docker-compose -f docker-compose.dev.yml up -d

# Detener
docker-compose -f docker-compose.dev.yml down

# Reiniciar
docker-compose -f docker-compose.dev.yml restart

# Reiniciar solo API
docker-compose -f docker-compose.dev.yml restart api
```

### Logs
```bash
# Todos los servicios
docker-compose -f docker-compose.dev.yml logs -f

# Solo API
docker-compose -f docker-compose.dev.yml logs -f api

# Solo MySQL
docker-compose -f docker-compose.dev.yml logs -f mysql

# Últimas 100 líneas
docker-compose -f docker-compose.dev.yml logs --tail=100 api

# Sin seguir (snapshot)
docker-compose -f docker-compose.dev.yml logs --no-follow api
```

### Shell/Terminal
```bash
# Bash en API container
docker-compose -f docker-compose.dev.yml exec api bash

# MySQL shell
docker-compose -f docker-compose.dev.yml exec mysql mysql -u soat_user -p

# Python REPL
docker-compose -f docker-compose.dev.yml exec api python

# Ejecutar comando único
docker-compose -f docker-compose.dev.yml exec api ls -la
```

### Testing
```bash
# Todos los tests
docker-compose -f docker-compose.dev.yml exec api pytest

# Con coverage
docker-compose -f docker-compose.dev.yml exec api pytest --cov=app

# Tests específicos
docker-compose -f docker-compose.dev.yml exec api pytest tests/test_owner_validation.py

# Verbose
docker-compose -f docker-compose.dev.yml exec api pytest -v -s
```

### Reconstruir
```bash
# Reconstruir imagen
docker-compose -f docker-compose.dev.yml build

# Reconstruir sin cache
docker-compose -f docker-compose.dev.yml build --no-cache

# Reconstruir solo API
docker-compose -f docker-compose.dev.yml build api

# Reconstruir e iniciar
docker-compose -f docker-compose.dev.yml up -d --build
```

---

## 🚀 Producción

### Iniciar/Detener
```bash
# Iniciar
docker-compose up -d

# Detener
docker-compose down

# Reiniciar
docker-compose restart

# Iniciar con phpMyAdmin
docker-compose --profile debug up -d
```

### Logs
```bash
# Todos los servicios
docker-compose logs -f

# Solo API
docker-compose logs -f api

# Solo MySQL
docker-compose logs -f mysql

# Últimas N líneas
docker-compose logs --tail=50 api
```

### Shell/Terminal
```bash
# Bash en API
docker-compose exec api bash

# MySQL shell
docker-compose exec mysql mysql -u soat_user -p

# Ejecutar comando
docker-compose exec api python --version
```

### Reconstruir
```bash
# Reconstruir
docker-compose build

# Sin cache
docker-compose build --no-cache

# Reconstruir e iniciar
docker-compose up -d --build
```

---

## 📊 Monitoreo

### Estado de Servicios
```bash
# Producción
docker-compose ps

# Desarrollo
docker-compose -f docker-compose.dev.yml ps

# Formato detallado
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
```

### Recursos
```bash
# Todos los containers
docker stats

# Solo SOAT containers
docker stats soat_api soat_mysql

# Snapshot (sin actualización)
docker stats --no-stream
```

### Inspección
```bash
# Inspeccionar API container
docker inspect soat_api

# Ver IP del container
docker inspect soat_api | grep IPAddress

# Ver health status
docker inspect soat_api | grep -A 10 Health

# Ver montajes de volúmenes
docker inspect soat_api | grep -A 20 Mounts

# Ver variables de entorno
docker inspect soat_api | grep -A 50 Env
```

### Logs del Sistema
```bash
# Eventos de Docker
docker events

# Eventos filtrados
docker events --filter container=soat_api

# Información del sistema
docker info

# Uso de disco
docker system df
```

---

## 🗄️ Base de Datos

### Conexión
```bash
# Desde host (si puerto expuesto)
mysql -h localhost -P 3306 -u soat_user -p

# Desde API container
docker-compose exec api mysql -h mysql -u soat_user -p

# Desde MySQL container
docker-compose exec mysql mysql -u soat_user -p
```

### Backup
```bash
# Exportar base de datos
docker-compose exec mysql mysqldump -u soat_user -p soat_db > backup_$(date +%Y%m%d).sql

# Exportar todas las bases
docker-compose exec mysql mysqldump -u root -p --all-databases > backup_all_$(date +%Y%m%d).sql

# Backup comprimido
docker-compose exec mysql mysqldump -u soat_user -p soat_db | gzip > backup_$(date +%Y%m%d).sql.gz
```

### Restore
```bash
# Importar base de datos
docker-compose exec -T mysql mysql -u soat_user -p soat_db < backup.sql

# Desde gzip
gunzip < backup.sql.gz | docker-compose exec -T mysql mysql -u soat_user -p soat_db
```

### Migraciones (Alembic)
```bash
# Ejecutar migraciones
docker-compose exec api alembic upgrade head

# Ver estado
docker-compose exec api alembic current

# Ver historial
docker-compose exec api alembic history

# Crear nueva migración
docker-compose exec api alembic revision --autogenerate -m "descripción"

# Revertir última migración
docker-compose exec api alembic downgrade -1
```

---

## 🔍 Debugging

### Ver Logs en Tiempo Real
```bash
# API logs
docker-compose logs -f --tail=100 api

# MySQL logs
docker-compose logs -f --tail=100 mysql

# Grep en logs
docker-compose logs api | grep ERROR
docker-compose logs api | grep -i "validation"
```

### Conectividad
```bash
# Ping entre containers
docker-compose exec api ping mysql

# Test de puerto
docker-compose exec api nc -zv mysql 3306

# Curl desde container
docker-compose exec api curl http://localhost:8000/api/v1/health

# DNS lookup
docker-compose exec api nslookup mysql
```

### Variables de Entorno
```bash
# Ver todas las variables
docker-compose exec api env

# Buscar variable específica
docker-compose exec api env | grep DB_HOST

# Ver .env montado
docker-compose exec api cat /app/.env
```

### Procesos
```bash
# Ver procesos en container
docker-compose exec api ps aux

# Top del container
docker top soat_api

# Ver archivos abiertos
docker-compose exec api lsof
```

---

## 🧹 Limpieza

### Servicios
```bash
# Detener y eliminar containers
docker-compose down

# Detener y eliminar containers + volúmenes
docker-compose down -v

# Detener y eliminar containers + volúmenes + imágenes
docker-compose down -v --rmi all

# Desarrollo
docker-compose -f docker-compose.dev.yml down -v
```

### Containers
```bash
# Eliminar containers detenidos
docker container prune

# Eliminar container específico
docker rm soat_api

# Forzar eliminación
docker rm -f soat_api
```

### Imágenes
```bash
# Eliminar imágenes sin usar
docker image prune

# Eliminar todas las imágenes sin usar
docker image prune -a

# Eliminar imagen específica
docker rmi soat-v2_api

# Ver tamaño de imágenes
docker images --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}"
```

### Volúmenes
```bash
# Listar volúmenes
docker volume ls

# Eliminar volúmenes sin usar
docker volume prune

# Eliminar volumen específico
docker volume rm soat-v2_mysql_data

# Inspeccionar volumen
docker volume inspect soat-v2_mysql_data
```

### Redes
```bash
# Listar redes
docker network ls

# Eliminar redes sin usar
docker network prune

# Inspeccionar red
docker network inspect soat_network
```

### Sistema Completo
```bash
# Limpiar todo (⚠️ peligroso)
docker system prune -af --volumes

# Limpiar containers e imágenes
docker system prune -af

# Ver espacio usado
docker system df

# Información detallada
docker system df -v
```

---

## 🔧 Utilidades

### Copiar Archivos
```bash
# Del container al host
docker cp soat_api:/app/logs/app.log ./local_log.log

# Del host al container
docker cp local_file.txt soat_api:/app/temp/

# Copiar carpeta
docker cp soat_api:/app/logs ./local_logs/
```

### Ejecutar Comandos
```bash
# Python script
docker-compose exec api python scripts/create_dynamodb_tables.py

# Bash script
docker-compose exec api bash scripts/setup.sh

# Como otro usuario
docker-compose exec --user root api apt-get update
```

### Variables de Entorno
```bash
# Pasar variable temporal
docker-compose exec -e DEBUG=true api python script.py

# Ver variable
docker-compose exec api printenv DB_HOST
```

---

## 📦 Build y Push

### Build
```bash
# Build local
docker build -t soat-v2-api:latest .

# Build dev
docker build -f Dockerfile.dev -t soat-v2-api:dev .

# Build sin cache
docker build --no-cache -t soat-v2-api:latest .

# Build con argumentos
docker build --build-arg PYTHON_VERSION=3.11 -t soat-v2-api:latest .
```

### Tag
```bash
# Tag para registry
docker tag soat-v2-api:latest registry.example.com/soat-v2-api:latest

# Tag con versión
docker tag soat-v2-api:latest registry.example.com/soat-v2-api:1.0.0

# Ver tags
docker images soat-v2-api
```

### Push (Registry/ECR)
```bash
# Push a Docker Hub
docker push username/soat-v2-api:latest

# Push a ECR (AWS)
# 1. Login
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <account-id>.dkr.ecr.us-east-1.amazonaws.com

# 2. Tag
docker tag soat-v2-api:latest <account-id>.dkr.ecr.us-east-1.amazonaws.com/soat-v2-api:latest

# 3. Push
docker push <account-id>.dkr.ecr.us-east-1.amazonaws.com/soat-v2-api:latest
```

---

## 🎯 Troubleshooting

### Puerto Ocupado
```bash
# Windows
netstat -ano | findstr :8000
taskkill /PID <PID> /F

# Linux/macOS
lsof -i :8000
kill -9 <PID>
```

### Container No Inicia
```bash
# Ver logs completos
docker-compose logs api

# Ver últimos 50 errores
docker-compose logs --tail=50 api | grep -i error

# Reiniciar
docker-compose restart api

# Recrear
docker-compose up -d --force-recreate api
```

### Health Check Fallando
```bash
# Verificar health
docker inspect soat_api | grep -A 10 Health

# Probar manualmente
docker-compose exec api curl http://localhost:8000/api/v1/health

# Ver logs de health check
docker events --filter container=soat_api
```

### Base de Datos No Conecta
```bash
# Verificar MySQL
docker-compose ps mysql

# Ping desde API
docker-compose exec api ping mysql

# Test puerto
docker-compose exec api nc -zv mysql 3306

# Ver logs de MySQL
docker-compose logs mysql | grep -i error
```

### Cambios No Se Reflejan
```bash
# Verificar volúmenes montados
docker inspect soat_api_dev | grep -A 20 Mounts

# Reiniciar con rebuild
docker-compose -f docker-compose.dev.yml up -d --build

# Ver si uvicorn detecta cambios
docker-compose -f docker-compose.dev.yml logs -f api | grep reload
```

---

## 🔑 Comandos con Makefile

```bash
# Ver todos los comandos
make help

# DESARROLLO
make dev-build dev-up dev-logs    # Build, start, logs
make dev-shell                     # Shell
make dev-test                      # Tests
make dev-down                      # Stop

# PRODUCCIÓN
make build up logs                 # Build, start, logs
make shell                         # Shell
make test                          # Tests
make down                          # Stop

# BASE DE DATOS
make db-migrate                    # Run migrations
make db-revision msg="descripción" # Create migration

# LIMPIEZA
make clean                         # Clean all (prod)
make dev-clean                     # Clean all (dev)
make prune                         # Prune Docker system
```

---

## 🌐 URLs de Acceso

```bash
# API
http://localhost:8000
http://localhost:8000/api/docs
http://localhost:8000/api/redoc
http://localhost:8000/api/v1/health

# phpMyAdmin
http://localhost:8080

# Health Check
curl http://localhost:8000/api/v1/health
```

---

## 📱 Atajos Personalizados (Bash/Zsh)

Agregar a `~/.bashrc` o `~/.zshrc`:

```bash
# SOAT aliases
alias soat-dev-up='docker-compose -f docker-compose.dev.yml up -d'
alias soat-dev-down='docker-compose -f docker-compose.dev.yml down'
alias soat-dev-logs='docker-compose -f docker-compose.dev.yml logs -f api'
alias soat-dev-shell='docker-compose -f docker-compose.dev.yml exec api bash'
alias soat-dev-test='docker-compose -f docker-compose.dev.yml exec api pytest'

alias soat-up='docker-compose up -d'
alias soat-down='docker-compose down'
alias soat-logs='docker-compose logs -f api'
alias soat-shell='docker-compose exec api bash'
alias soat-db='docker-compose exec mysql mysql -u soat_user -p'

# Funciones útiles
soat-rebuild() {
    docker-compose -f docker-compose.dev.yml down
    docker-compose -f docker-compose.dev.yml build --no-cache
    docker-compose -f docker-compose.dev.yml up -d
}

soat-fresh() {
    docker-compose down -v
    docker volume rm soat-v2_mysql_data 2>/dev/null
    docker-compose build --no-cache
    docker-compose up -d
}
```

**Windows (PowerShell Profile):**

Agregar a `$PROFILE`:

```powershell
# SOAT functions
function soat-dev-up { docker-compose -f docker-compose.dev.yml up -d }
function soat-dev-down { docker-compose -f docker-compose.dev.yml down }
function soat-dev-logs { docker-compose -f docker-compose.dev.yml logs -f api }
function soat-dev-shell { docker-compose -f docker-compose.dev.yml exec api bash }

function soat-up { docker-compose up -d }
function soat-down { docker-compose down }
function soat-logs { docker-compose logs -f api }
function soat-shell { docker-compose exec api bash }
```

---

## 💡 Tips Avanzados

### Ver cambios en tiempo real
```bash
# Logs + grep + highlight
docker-compose logs -f api | grep --color=always -E 'ERROR|WARNING|$'
```

### Backup automático
```bash
# Crear script backup.sh
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
docker-compose exec mysql mysqldump -u soat_user -p soat_db | gzip > backups/backup_$DATE.sql.gz
```

### Monitoreo continuo
```bash
# Watch health status
watch -n 5 'docker-compose ps'

# Watch stats
watch -n 2 'docker stats --no-stream soat_api soat_mysql'
```

### Multi-tail logs
```bash
# Ver logs de múltiples servicios
docker-compose logs -f api mysql
```

---

**Fecha:** 2025-10-18  
**Versión:** 1.0  
**Última actualización:** 2025-10-18

**💾 Guardar como favorito o imprimir para tener a mano!**
