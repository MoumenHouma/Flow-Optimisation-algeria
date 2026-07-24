# Multi-stage build -> static assets served by nginx (docs/RULES.md §4.1)
FROM node:20-slim AS builder

WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm ci || npm install
COPY . .
# Vite bakes VITE_* at build time, so the API origin must be a build arg (not a
# runtime env_file var). Empty = same-origin relative /api (the app is served
# behind the same gateway); set to the public origin for a split frontend/API.
ARG VITE_API_BASE_URL
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
RUN npm run build

FROM nginx:1.27-alpine AS runtime
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 5173
CMD ["nginx", "-g", "daemon off;"]
