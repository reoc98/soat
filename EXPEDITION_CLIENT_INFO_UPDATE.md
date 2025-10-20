# Actualización de Información del Cliente en Pre-Expedición

## Resumen de Cambios

Se ha actualizado el endpoint de pre-expedición para recibir y almacenar información adicional del cliente antes de proceder con la validación de las pólizas.

## Cambios Realizados

### 1. Schema de Pre-Expedición (`app/schemas/expedition.py`)

Se agregaron los siguientes campos obligatorios al `PreExpeditionRequest`:

- **`address`** (str, requerido): Dirección del cliente
  - Longitud: 1-100 caracteres
  
- **`phone`** (str, requerido): Número de celular del cliente
  - Longitud: 7-20 caracteres
  - Solo dígitos (se valida y limpia automáticamente)
  
- **`email`** (str, requerido): Correo electrónico del cliente
  - Longitud: 5-255 caracteres
  - Validación básica de formato email

- **`city_id`** (int, requerido): ID de la ciudad del cliente
  - Debe ser mayor a 0
  - Debe existir en la tabla `cities`
  
- **`birth_date`** (str, opcional): Fecha de nacimiento
  - Formato: YYYY-MM-DD
  - **REQUERIDO** cuando se selecciona el producto AP (Accidentes Personales)
  - Opcional para otros productos

### 2. Validaciones Implementadas

- **Email**: Validación básica de formato (debe contener @ y .)
- **Teléfono**: Solo números (se eliminan espacios y guiones automáticamente)
- **Ciudad**: 
  - Debe ser un ID válido (mayor a 0)
  - Debe existir en la tabla `cities` de la base de datos
- **Fecha de nacimiento**: 
  - Validación de formato YYYY-MM-DD
  - Obligatoria cuando se incluye AP en las selecciones
- **Productos únicos**: No se permiten productos duplicados en la lista de selecciones

### 3. Servicio de Expedición (`app/services/expedition.py`)

Se agregó el método `update_client_info` que:

- Busca la sesión y el cliente asociado
- Valida que el city_id exista en la tabla `cities`
- Actualiza los campos del cliente en la base de datos
- Convierte la fecha de nacimiento de string a objeto date
- Registra logs de auditoría
- Maneja errores de formato de fecha y ciudad no encontrada

### 4. Endpoint API (`app/api/v1/endpoints/expedition.py`)

Se actualizó el flujo del endpoint `/pre-expedition/{session_slug}`:

**Flujo Anterior:**
1. Seleccionar planes
2. Pre-expedir pólizas

**Flujo Nuevo:**
1. Seleccionar planes
2. **Actualizar información del cliente** ← NUEVO
3. Pre-expedir pólizas

### 5. Modelo de Cliente (`app/models/client.py`)

El modelo ya contaba con los campos necesarios:
- `address` (VARCHAR 100)
- `phone` (VARCHAR 20)
- `email` (VARCHAR 255)
- `city_id` (INT, ForeignKey a cities.id)
- `birth_date` (DATE)

No se requirieron cambios en la estructura de la tabla.

## Ejemplo de Uso

### Request - SOAT únicamente

```json
POST /api/v1/expedition/pre-expedition/{session_slug}
{
  "selections": [
    {
      "product_code": "SOAT",
      "option_id": 125
    }
  ],
  "address": "Calle 123 #45-67, Apt 301",
  "phone": "3001234567",
  "email": "cliente@example.com",
  "city_id": 1
}
```

### Request - SOAT + AP (fecha de nacimiento requerida)

```json
POST /api/v1/expedition/pre-expedition/{session_slug}
{
  "selections": [
    {
      "product_code": "SOAT",
      "option_id": 125
    },
    {
      "product_code": "AP",
      "option_id": 124
    }
  ],
  "address": "Calle 123 #45-67, Apt 301",
  "phone": "3001234567",
  "email": "cliente@example.com",
  "city_id": 1,
  "birth_date": "1990-05-15"
}
```

### Request - SOAT + AP + RCE

```json
POST /api/v1/expedition/pre-expedition/{session_slug}
{
  "selections": [
    {
      "product_code": "SOAT",
      "option_id": 125
    },
    {
      "product_code": "AP",
      "option_id": 124
    },
    {
      "product_code": "RCE",
      "option_id": 130
    }
  ],
  "address": "Carrera 45 #78-90",
  "phone": "3159876543",
  "email": "usuario@dominio.com",
  "city_id": 2,
  "birth_date": "1985-12-20"
}
```

## Validaciones y Errores

### Error 400 - Validación

**Email inválido:**
```json
{
  "detail": "Email inválido"
}
```

**Teléfono inválido:**
```json
{
  "detail": "El teléfono debe contener solo números"
}
```

**Fecha de nacimiento requerida para AP:**
```json
{
  "detail": "La fecha de nacimiento es requerida cuando se selecciona AP"
}
```

**Formato de fecha inválido:**
```json
{
  "detail": "Formato de fecha de nacimiento inválido. Use YYYY-MM-DD"
}
```

**Ciudad no encontrada:**
```json
{
  "detail": "Ciudad con ID 999 no encontrada"
}
```

### Error 404 - No Encontrado

```json
{
  "detail": "Sesión no encontrada"
}
```

```json
{
  "detail": "Cliente no encontrado en la sesión"
}
```

## Proceso Completo de Pre-Expedición

1. **Usuario crea cotización** → Obtiene opciones de planes disponibles
2. **Usuario selecciona planes** → Elige las opciones que desea contratar
3. **Usuario proporciona información de contacto** → Dirección, teléfono, email, fecha de nacimiento (si aplica)
4. **POST /pre-expedition** → Se envían las selecciones y la información del cliente
5. **Sistema valida y guarda** → Se actualizan los datos del cliente en la base de datos
6. **Sistema pre-expide** → Se valida con Mundial Seguros (cotizador=true)
7. **Usuario es redirigido a pago** → Si todo es exitoso
8. **POST /expedition** → Después de confirmar el pago, se emiten las pólizas finales

## Notas Técnicas

- Los campos se validan antes de enviarse a la base de datos
- El teléfono se limpia automáticamente (se eliminan espacios y guiones)
- El email se convierte a minúsculas
- La fecha de nacimiento se almacena como tipo DATE en la base de datos
- Todos los cambios se registran en los logs para auditoría
- El proceso es transaccional (si falla alguna parte, no se guarda nada)

## Archivos Modificados

1. `app/schemas/expedition.py` - Schema de request actualizado
2. `app/services/expedition.py` - Nuevo método para actualizar cliente
3. `app/api/v1/endpoints/expedition.py` - Endpoint actualizado con nuevo flujo

## Archivos Sin Cambios

- `app/models/client.py` - Ya contenía los campos necesarios
- Base de datos - No requiere migraciones

## Compatibilidad

- ✅ Retrocompatible con el flujo de expedición existente
- ✅ No afecta otros endpoints
- ✅ No requiere cambios en la base de datos
- ⚠️ **Breaking change**: El endpoint de pre-expedición ahora requiere los campos adicionales

## Testing

Para probar los cambios:

```bash
# 1. Asegúrate de que el servidor esté corriendo
python -m app.main

# 2. Prueba con SOAT solo (sin fecha de nacimiento)
curl -X POST http://localhost:8000/api/v1/expedition/pre-expedition/{session_slug} \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{
    "selections": [{"product_code": "SOAT", "option_id": 125}],
    "address": "Calle 123",
    "phone": "3001234567",
    "email": "test@example.com",
    "city_id": 1
  }'

# 3. Prueba con SOAT + AP (con fecha de nacimiento)
curl -X POST http://localhost:8000/api/v1/expedition/pre-expedition/{session_slug} \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{
    "selections": [
      {"product_code": "SOAT", "option_id": 125},
      {"product_code": "AP", "option_id": 124}
    ],
    "address": "Calle 123",
    "phone": "3001234567",
    "email": "test@example.com",
    "city_id": 1,
    "birth_date": "1990-05-15"
  }'
```

## Próximos Pasos

Si necesitas realizar cambios adicionales:

1. **Agregar más validaciones**: Edita los validators en `app/schemas/expedition.py`
2. **Cambiar campos obligatorios**: Modifica los Field() en `PreExpeditionRequest`
3. **Agregar más campos**: Actualiza el schema, el método update_client_info, y la tabla si es necesario
