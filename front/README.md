# SOAT Frontend Docker Image

Este módulo contiene una imagen Docker ligera para servir la maqueta estática del marketplace de SOAT.

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

Luego abre tu navegador en `http://localhost:8080` para ver la maqueta.

## Personalización
Si necesitas modificar archivos estáticos mientras desarrollas, recuerda reconstruir la imagen después de cada cambio o monta los archivos como volumen:

```bash
docker run --rm -p 8080:80 \
  -v $(pwd)/front/index.html:/usr/share/nginx/html/index.html \
  -v $(pwd)/front/styles.css:/usr/share/nginx/html/styles.css \
  -v $(pwd)/front/app.js:/usr/share/nginx/html/app.js \
  soat-front
```

Esto te permitirá ver los cambios sin reconstruir la imagen.
