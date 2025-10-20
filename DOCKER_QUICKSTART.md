# 🐳 Docker Quick Start

Guía rápida para iniciar el proyecto con Docker en menos de 5 minutos.

---

## 🚀 Inicio Rápido (3 Pasos)

### 1️⃣ Crear archivo .env

**Windows (PowerShell):**
```powershell
Copy-Item .env.example .env
```

**Linux/macOS:**
```bash
cp .env.example .env
```

### 2️⃣ Ejecutar script de inicio

**Windows:**
```cmd
start.bat
```

**Linux/macOS:**
```bash
chmod +x start.sh
./start.sh
```

### 3️⃣ Acceder a la aplicación

- **API:** http://localhost:8000
- **Swagger Docs:** http://localhost:8000/api/docs
- **phpMyAdmin:** http://localhost:8080

---

## 📋 Comandos Básicos

### Desarrollo (con hot-reload)

```bash
# Iniciar
docker-compose -f docker-compose.dev.yml up -d

# Ver logs
docker-compose -f docker-compose.dev.yml logs -f

# Detener
docker-compose -f docker-compose.dev.yml down
```

### Producción

```bash
# Iniciar
docker-compose up -d

# Ver logs
docker-compose logs -f

# Detener
docker-compose down
```

---

## 🛠️ Usando Makefile (Recomendado)

Si tienes `make` instalado:

```bash
# Desarrollo
make dev-build    # Construir
make dev-up       # Iniciar
make dev-logs     # Ver logs
make dev-down     # Detener

# Producción
make build        # Construir
make up           # Iniciar
make logs         # Ver logs
make down         # Detener
```

---

## 🔍 Verificar que Todo Funciona

### 1. Verificar servicios

```bash
docker-compose ps
```

Deberías ver 3 servicios corriendo:
- ✅ `soat_api` (healthy)
- ✅ `soat_mysql` (healthy)
- ✅ `soat_phpmyadmin` (running)

### 2. Health Check

```bash
curl http://localhost:8000/api/v1/health
```

Respuesta esperada:
```json
{
  "status": "healthy",
  "timestamp": "2025-10-18T10:00:00Z"
}
```

### 3. Acceder a Swagger

Abrir navegador: http://localhost:8000/api/docs

### 4. Verificar MySQL

Abrir navegador: http://localhost:8080

**Credenciales:**
- Usuario: `soat_user`
- Contraseña: `soat_password`

---

## ⚡ Solución Rápida de Problemas

### Puerto ya en uso

**Cambiar puerto en `.env`:**
```env
API_PORT=8001
MYSQL_PORT=3307
PHPMYADMIN_PORT=8081
```

### Ver logs de errores

```bash
docker-compose logs api
```

### Reiniciar todo

```bash
docker-compose down
docker-compose up -d
```

### Limpiar todo y empezar de nuevo

```bash
docker-compose down -v
docker-compose build --no-cache
docker-compose up -d
```

---

## 📚 Documentación Completa

Para configuración avanzada, troubleshooting detallado, y deployment:

👉 Ver [DOCKER_SETUP.md](DOCKER_SETUP.md)

---

## 🎯 Siguiente Paso

Una vez que los servicios están corriendo, puedes:

1. **Explorar la API:** http://localhost:8000/api/docs
2. **Crear una sesión de seguro**
3. **Validar propietario**
4. **Generar cotización**
5. **Seleccionar planes**
6. **Pre-expedir pólizas**

Ver documentación completa de los servicios en los archivos `*_README.md` del proyecto.

---

**Fecha:** 2025-10-18  
**Última actualización:** 2025-10-18
