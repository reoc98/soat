# SOAT Frontend Docker Image

Este módulo contiene una imagen Docker ligera para servir la maqueta estática del marketplace de SOAT.

Incluye seis vistas enlazadas entre sí:
- `index.html`: página de inicio con beneficios y llamado a la acción.
- `cotizador.html`: formulario inicial que solicita placa, tipo y número de documento y valida al propietario contra la API.
- `detalle.html`: resumen del propietario y vehículo con tarjetas estilizadas, selección de homologación, cotización automática de SOAT/AP y posibilidad de continuar al resumen.
- `resumen.html`: vista de resumen de compra que muestra los productos seleccionados, total y captura dirección, ciudad, contacto, género y fecha de nacimiento (si aplica) antes de ejecutar la pre-expedición.
- `pago.html`: pantalla mock que simula el proceso de pago utilizando el token generado y redirige automáticamente al finalizar.
- `exito.html`: confirmación final de póliza expedida con detalle de coberturas, totales y enlace para volver al inicio.

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
- `http://localhost:8080/detalle.html` para revisar clases y cotizar.
- `http://localhost:8080/resumen.html` para confirmar datos y lanzar la pre-expedición.
- `http://localhost:8080/pago.html` para ver la animación de pago.
- `http://localhost:8080/exito.html` para la confirmación de póliza.

## Personalización
Si necesitas modificar archivos estáticos mientras desarrollas, recuerda reconstruir la imagen después de cada cambio o monta los archivos como volumen:

```bash
docker run --rm -p 8080:80 \
  -v $(pwd)/front/index.html:/usr/share/nginx/html/index.html \
  -v $(pwd)/front/cotizador.html:/usr/share/nginx/html/cotizador.html \
  -v $(pwd)/front/detalle.html:/usr/share/nginx/html/detalle.html \
  -v $(pwd)/front/resumen.html:/usr/share/nginx/html/resumen.html \
  -v $(pwd)/front/pago.html:/usr/share/nginx/html/pago.html \
  -v $(pwd)/front/exito.html:/usr/share/nginx/html/exito.html \
  -v $(pwd)/front/styles.css:/usr/share/nginx/html/styles.css \
  -v $(pwd)/front/app.js:/usr/share/nginx/html/app.js \
  soat-front
```

Esto te permitirá ver los cambios sin reconstruir la imagen.
