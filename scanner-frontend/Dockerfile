# Stage 1: Angular front-end
FROM node:17

WORKDIR /src

# Install app dependencies
# A wildcard is used to ensure both package.json AND package-lock.json are copied
# where available (npm@5+)
COPY package*.json ./

RUN npm install -g @angular/cli
# Compilation - increase the allocated memory otherwise might run out of memory
ENV NODE_OPTIONS="--max-old-space-size=1024"
RUN npm install

# Bundle app source
COPY . .

RUN ng build --prod

# Stage 2: nginx webserver
FROM nginx:1.19-alpine

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 CMD curl -f http://localhost/ping || exit 1

# NGINX configuration
COPY ./nginx.conf /etc/nginx/nginx.conf

# Static content
COPY --from=0 /src/dist/scanner-frontend/ /usr/share/nginx/html/