# ✅ Checklist de Setup - SOAT v2

Guía paso a paso para verificar la instalación y configuración correcta del proyecto.

---

## 📋 Pre-Instalación

### Requisitos del Sistema

- [ ] **Sistema Operativo:**
  - [ ] Windows 10/11 con WSL2 habilitado
  - [ ] Linux (Ubuntu 20.04+, Debian, etc.)
  - [ ] macOS 11+

- [ ] **Hardware:**
  - [ ] 4GB+ RAM disponible (8GB recomendado)
  - [ ] 10GB+ espacio en disco
  - [ ] CPU con 2+ cores

- [ ] **Software:**
  - [ ] Docker Desktop instalado y corriendo
  - [ ] Docker Compose disponible
  - [ ] Git instalado
  - [ ] Editor de código (VS Code recomendado)

### Verificar Instalación de Docker

```bash
# Ejecutar en terminal
docker --version
# Salida esperada: Docker version 20.10.x o superior

docker-compose --version
# Salida esperada: docker-compose version 1.29.x o superior

docker ps
# Si funciona sin errores, Docker está corriendo correctamente
```

**Windows adicional:**
```powershell
# Verificar que WSL2 esté activo
wsl --list --verbose
# Debe mostrar distribución con VERSION 2
```

---

## 🚀 Instalación con Docker

### Paso 1: Obtener el Código

- [ ] Clonar repositorio
```bash
git clone <repository-url>
cd soat-v2
```

- [ ] Verificar estructura
```bash
ls -la
# Debe mostrar: Dockerfile, docker-compose.yml, app/, etc.
```

### Paso 2: Configurar Variables de Entorno

- [ ] Copiar archivo de ejemplo
```bash
# Windows PowerShell
Copy-Item .env.example .env

# Linux/macOS
cp .env.example .env
```

- [ ] Editar `.env` con tu configuración
  - [ ] Revisar puertos (8000, 3306, 8080)
  - [ ] Configurar credenciales de MySQL
  - [ ] Configurar AWS (si aplica)

- [ ] Verificar que `.env` no esté en git
```bash
git status
# .env NO debe aparecer en la lista
```

### Paso 3: Verificar Puertos Disponibles

**Windows:**
```powershell
# Verificar puerto 8000
netstat -ano | findstr :8000
# Si no devuelve nada, el puerto está libre

# Verificar puerto 3306
netstat -ano | findstr :3306

# Verificar puerto 8080
netstat -ano | findstr :8080
```

**Linux/macOS:**
```bash
# Verificar puertos
lsof -i :8000
lsof -i :3306
lsof -i :8080
# Si no devuelven nada, los puertos están libres
```

- [ ] Si algún puerto está ocupado, cambiar en `.env`:
```env
API_PORT=8001
MYSQL_PORT=3307
PHPMYADMIN_PORT=8081
```

### Paso 4: Iniciar Servicios

**Opción A: Usar Scripts (Más fácil)**

- [ ] **Windows:**
```cmd
start.bat
# Elegir opción 1 (Development) o 2 (Production)
```

- [ ] **Linux/macOS:**
```bash
chmod +x start.sh
./start.sh
# Elegir opción 1 (Development) o 2 (Production)
```

**Opción B: Comandos Manuales**

- [ ] **Desarrollo:**
```bash
docker-compose -f docker-compose.dev.yml build
docker-compose -f docker-compose.dev.yml up -d
```

- [ ] **Producción:**
```bash
docker-compose build
docker-compose up -d
```

### Paso 5: Verificar Servicios

- [ ] Ver estado de servicios
```bash
# Desarrollo
docker-compose -f docker-compose.dev.yml ps

# Producción
docker-compose ps
```

**Salida esperada:**
```
NAME                 STATUS              PORTS
soat_mysql           Up (healthy)        0.0.0.0:3306->3306/tcp
soat_api             Up (healthy)        0.0.0.0:8000->8000/tcp
soat_phpmyadmin      Up                  0.0.0.0:8080->80/tcp
```

- [ ] Todos los servicios deben estar `Up`
- [ ] MySQL y API deben mostrar `(healthy)`

### Paso 6: Verificar Logs

- [ ] Ver logs de todos los servicios
```bash
docker-compose logs
```

- [ ] Ver logs solo de API
```bash
docker-compose logs api
```

- [ ] **No deben aparecer errores críticos**
- [ ] Debe mostrar: "Application startup complete"

---

## 🧪 Verificación de Funcionamiento

### Test 1: Health Check

- [ ] Ejecutar comando
```bash
curl http://localhost:8000/api/v1/health
```

**Salida esperada:**
```json
{
  "status": "healthy",
  "timestamp": "2025-10-18T10:00:00Z"
}
```

### Test 2: Swagger Docs

- [ ] Abrir navegador: http://localhost:8000/api/docs
- [ ] Debe cargar la documentación Swagger
- [ ] Debe mostrar todos los endpoints
- [ ] Debe tener botón "Authorize" visible

### Test 3: ReDoc

- [ ] Abrir navegador: http://localhost:8000/api/redoc
- [ ] Debe cargar documentación alternativa
- [ ] Debe mostrar estructura de API organizada

### Test 4: phpMyAdmin

- [ ] Abrir navegador: http://localhost:8080
- [ ] Login con credenciales de `.env`:
  - Usuario: `soat_user` (o tu configuración)
  - Contraseña: `soat_password` (o tu configuración)
- [ ] Debe mostrar base de datos `soat_db`
- [ ] Debe poder explorar tablas

### Test 5: Conectividad de Base de Datos

- [ ] Entrar al contenedor
```bash
docker-compose exec api bash
```

- [ ] Dentro del contenedor, verificar conexión
```bash
mysql -h mysql -u soat_user -p
# Ingresar password cuando pregunte
```

- [ ] Ejecutar query de prueba
```sql
SHOW DATABASES;
USE soat_db;
SHOW TABLES;
```

- [ ] Salir
```bash
exit  # Salir de MySQL
exit  # Salir del contenedor
```

---

## 🔧 Tests Funcionales

### Test 6: Endpoint Público (Sin Auth)

- [ ] Health check funciona sin token
```bash
curl http://localhost:8000/api/v1/health
```
**Debe funcionar SIN autenticación**

### Test 7: Endpoint Protegido (Con Auth)

Si tienes configurado Cognito:

- [ ] Intentar acceder sin token (debe fallar)
```bash
curl http://localhost:8000/api/v1/session/info/test-slug
```
**Debe retornar 401 Unauthorized**

- [ ] Con token (debe funcionar)
```bash
curl -H "Authorization: Bearer <tu-token>" \
     http://localhost:8000/api/v1/session/info/test-slug
```

Si NO tienes Cognito (USE_COGNITO=false):

- [ ] Endpoints funcionan sin autenticación (según configuración)

### Test 8: Hot Reload (Solo Desarrollo)

Si estás en modo desarrollo:

- [ ] Editar archivo `app/main.py`
- [ ] Agregar print en alguna función
- [ ] Guardar archivo
- [ ] Ver logs en tiempo real
```bash
docker-compose -f docker-compose.dev.yml logs -f api
```
- [ ] Debe mostrar: "Reloading"
- [ ] Debe reiniciar automáticamente

---

## 🐛 Troubleshooting Checklist

### Si los Servicios No Inician

- [ ] Verificar Docker está corriendo
```bash
docker info
```

- [ ] Verificar espacio en disco
```bash
docker system df
```

- [ ] Ver logs de error
```bash
docker-compose logs
```

- [ ] Recrear desde cero
```bash
docker-compose down -v
docker-compose build --no-cache
docker-compose up -d
```

### Si MySQL No Está Healthy

- [ ] Ver logs de MySQL
```bash
docker-compose logs mysql
```

- [ ] Verificar variables en `.env`
  - [ ] MYSQL_ROOT_PASSWORD configurado
  - [ ] MYSQL_DATABASE configurado
  - [ ] MYSQL_USER y MYSQL_PASSWORD configurados

- [ ] Eliminar volumen y recrear
```bash
docker-compose down -v
docker volume rm soat-v2_mysql_data
docker-compose up -d
```

### Si API No Está Healthy

- [ ] Ver logs de API
```bash
docker-compose logs api
```

- [ ] Verificar que MySQL esté healthy primero
```bash
docker-compose ps
```

- [ ] Verificar conexión a MySQL
```bash
docker-compose exec api ping mysql
```

- [ ] Reintentar health check manual
```bash
docker-compose exec api curl http://localhost:8000/api/v1/health
```

### Si Hot Reload No Funciona

- [ ] Verificar que estás usando `docker-compose.dev.yml`
- [ ] Verificar montaje de volúmenes
```bash
docker inspect soat_api_dev | grep -A 20 Mounts
```
- [ ] Debe mostrar montaje de `./app:/app/app`

- [ ] Reiniciar servicio
```bash
docker-compose -f docker-compose.dev.yml restart api
```

---

## 📊 Checklist de Configuración Avanzada

### AWS Integration (Opcional)

Si vas a usar AWS:

- [ ] **Secrets Manager:**
  - [ ] Crear secreto en AWS Secrets Manager
  - [ ] Configurar `USE_SECRETS_MANAGER=true` en `.env`
  - [ ] Agregar credenciales AWS en `.env`
  - [ ] Verificar acceso desde contenedor
  ```bash
  docker-compose exec api aws sts get-caller-identity
  ```

- [ ] **Cognito:**
  - [ ] Crear User Pool en Cognito
  - [ ] Obtener Pool ID y Client ID
  - [ ] Configurar en `.env`:
  ```env
  USE_COGNITO=true
  COGNITO_USER_POOL_ID=us-east-1_xxxxxxxxx
  COGNITO_APP_CLIENT_ID=xxxxxxxxxxxxxxxxxx
  ```
  - [ ] Crear usuario de prueba
  - [ ] Obtener token JWT
  - [ ] Probar endpoints protegidos

- [ ] **DynamoDB:**
  - [ ] Crear tablas en DynamoDB
  - [ ] Verificar permisos IAM
  - [ ] Probar escritura de logs

### Performance y Monitoreo

- [ ] Configurar límites de recursos en `docker-compose.yml`:
```yaml
deploy:
  resources:
    limits:
      cpus: '2'
      memory: 2G
```

- [ ] Habilitar métricas
```bash
docker stats
```

- [ ] Configurar log rotation
- [ ] Configurar alertas de health check

---

## 🎓 Checklist de Desarrollo

### Configuración de IDE

- [ ] **VS Code:**
  - [ ] Instalar extensión Python
  - [ ] Instalar extensión Docker
  - [ ] Configurar Python interpreter al venv del container
  - [ ] Instalar extensión REST Client para probar APIs

- [ ] **Git:**
  - [ ] Configurar `.gitignore` (ya incluido)
  - [ ] Verificar que `.env` NO esté trackeado
  - [ ] Configurar pre-commit hooks (opcional)

### Testing Setup

- [ ] Instalar dependencias de test (ya en Dockerfile.dev)
- [ ] Crear carpeta `tests/` si no existe
- [ ] Ejecutar tests de ejemplo
```bash
docker-compose -f docker-compose.dev.yml exec api pytest
```

- [ ] Configurar coverage
```bash
docker-compose -f docker-compose.dev.yml exec api pytest --cov=app
```

---

## ✅ Checklist Final

### Mínimo para Desarrollo Local

- [x] Docker instalado y corriendo
- [x] Repositorio clonado
- [x] `.env` configurado
- [x] Servicios iniciados con `start.bat` o `start.sh`
- [x] Health check respondiendo OK
- [x] Swagger docs accesible
- [x] MySQL conecta correctamente
- [x] Logs sin errores críticos

### Mínimo para Producción

- [ ] Todas las verificaciones de desarrollo
- [ ] Variables de entorno de producción configuradas
- [ ] `USE_SECRETS_MANAGER=true` (recomendado)
- [ ] `ENVIRONMENT=production`
- [ ] `DEBUG=false`
- [ ] `LOG_LEVEL=INFO` o `WARNING`
- [ ] Credenciales fuertes en MySQL
- [ ] CORS configurado con dominios específicos
- [ ] SSL/TLS configurado (en proxy/load balancer)
- [ ] Backups de base de datos configurados
- [ ] Monitoreo y alertas activos

---

## 📝 Notas Finales

### Comandos Rápidos de Referencia

```bash
# Ver estado
docker-compose ps

# Ver logs
docker-compose logs -f

# Reiniciar
docker-compose restart

# Detener
docker-compose down

# Limpiar todo
docker-compose down -v

# Reconstruir
docker-compose build --no-cache

# Shell en API
docker-compose exec api bash

# MySQL shell
docker-compose exec mysql mysql -u soat_user -p
```

### Recursos Útiles

- **Documentación Completa:** [DOCKER_SETUP.md](DOCKER_SETUP.md)
- **Inicio Rápido:** [DOCKER_QUICKSTART.md](DOCKER_QUICKSTART.md)
- **README Principal:** [README.md](README.md)
- **Servicios:** Ver archivos `*_README.md` y `*_GUIDE.md`

### Soporte

Si encuentras problemas:
1. Revisar logs: `docker-compose logs`
2. Consultar troubleshooting en [DOCKER_SETUP.md](DOCKER_SETUP.md)
3. Verificar este checklist nuevamente
4. Buscar error específico en documentación

---

**Fecha:** 2025-10-18  
**Versión:** 1.0  
**Última actualización:** 2025-10-18

¡Éxito con tu instalación! 🚀
