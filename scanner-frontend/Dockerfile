FROM nginx:1.21-alpine

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 CMD curl -f http://localhost/ping || exit 1

# NGINX configuration
COPY ./nginx.conf /etc/nginx/nginx.conf

# Static content
COPY ./dist/scanner-frontend/ /usr/share/nginx/html/