# SOAT Frontend Docker Image

Este módulo contiene una imagen Docker ligera para servir la maqueta estática del marketplace de SOAT.

Incluye tres vistas:
- `index.html`: página de inicio con beneficios y llamado a la acción.
- `cotizador.html`: formulario inicial que solicita placa, tipo y número de documento.
- `detalle.html`: resumen del propietario y vehículo con tarjetas estilizadas, selección de homologación y cotización automática que muestra los productos devueltos (SOAT destacado y AP opcional).

## Requisitos
- [Docker](https://docs.docker.com/get-docker/) instalado localmente.

## Construir la imagen
Ejecuta el siguiente comando desde la raíz del repositorio:

```bash
docker build -t soat-front ./front
```

## Ejecutar el contenedor
Para levantar el sitio en `http://localhost:8080`:

```bash
docker run --rm -p 8080:80 soat-front
```

Luego abre tu navegador en:
- `http://localhost:8080/index.html` para la página de inicio.
- `http://localhost:8080/cotizador.html` para el formulario.
- `http://localhost:8080/detalle.html` para la vista posterior a la validación (requiere sesión activa).

## Personalización
Si necesitas modificar archivos estáticos mientras desarrollas, recuerda reconstruir la imagen después de cada cambio o monta los archivos como volumen:

```bash
docker run --rm -p 8080:80 \
  -v $(pwd)/front/index.html:/usr/share/nginx/html/index.html \
  -v $(pwd)/front/cotizador.html:/usr/share/nginx/html/cotizador.html \
  -v $(pwd)/front/detalle.html:/usr/share/nginx/html/detalle.html \
  -v $(pwd)/front/styles.css:/usr/share/nginx/html/styles.css \
  -v $(pwd)/front/app.js:/usr/share/nginx/html/app.js \
  soat-front
```

Esto te permitirá ver los cambios sin reconstruir la imagen.
