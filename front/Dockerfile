# syntax=docker/dockerfile:1
FROM nginx:1.25-alpine

COPY index.html cotizador.html detalle.html styles.css app.js /usr/share/nginx/html/

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
