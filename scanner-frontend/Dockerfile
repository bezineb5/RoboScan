FROM nginx:1.19-alpine

EXPOSE 80

# NGINX configuration
COPY ./nginx.conf /etc/nginx/nginx.conf

# Static content
COPY ./dist/scanner-frontend/ /usr/share/nginx/html/