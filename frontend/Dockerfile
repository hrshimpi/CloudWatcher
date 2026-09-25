# syntax=docker/dockerfile:1

# ---- build: compile the Vite/React app ----
FROM node:20-alpine AS build

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .
RUN npm run build

# ---- runtime: serve the static build through nginx ----
FROM nginx:1.27-alpine AS runtime

RUN apk add --no-cache gettext # for envsubst

COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf.template /etc/nginx/templates/app.conf.template
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

# Overridden at deploy time (Terraform sets this to the api Cloud Run
# service's URL); this default only matters for a standalone `docker run`.
ENV API_BASE_URL=http://localhost:8000

EXPOSE 8080

ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["nginx", "-g", "daemon off;"]
