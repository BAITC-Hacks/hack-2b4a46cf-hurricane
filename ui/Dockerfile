# syntax=docker/dockerfile:1.7
# Stage 1: dependencies, installed as the non-root `node` user so Vite can write its caches later.
FROM node:22.17.1-alpine3.22 AS deps
RUN mkdir -p /app && chown node:node /app
WORKDIR /app
USER node
# Manifests first: this layer is cached until dependencies change.
COPY --chown=node:node package.json yarn.lock ./
RUN --mount=type=cache,target=/home/node/.cache/yarn,uid=1000,gid=1000 \
    yarn install --frozen-lockfile

# Stage `dev`: Vite dev server with hot reload, used by docker-compose.yml.
FROM deps AS dev
COPY --chown=node:node . .
EXPOSE 5173
CMD ["yarn", "dev", "--host", "0.0.0.0"]

# Stage 2: production build. Vite bakes VITE_* in at build time; Railway passes service
# variables into the build only for ARGs declared here.
FROM deps AS build
# hadolint ignore=DL3064
ARG VITE_API_URL
# hadolint ignore=DL3064
ENV VITE_API_URL=$VITE_API_URL
COPY --chown=node:node . .
RUN yarn build

# Stage `prod` (last, so it is the default target): static files behind nginx, non-root, listens on $PORT.
FROM nginxinc/nginx-unprivileged:1.29.1-alpine AS prod
ENV PORT=8080
COPY --from=build /app/dist /usr/share/nginx/html
COPY default.conf.template /etc/nginx/templates/default.conf.template
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=3s CMD ["sh", "-c", "wget -qO- http://localhost:$PORT/"]
