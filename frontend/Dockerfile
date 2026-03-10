FROM node:20-alpine AS build

WORKDIR /app

COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci

COPY frontend/ .

ARG VITE_API_BASE_URL=/api
ARG GOOGLE_CLIENT_ID
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
ENV VITE_GOOGLE_CLIENT_ID=$GOOGLE_CLIENT_ID

RUN npm run build

# Build mdBook documentation
FROM alpine:3.21 AS docs-build
ARG MDBOOK_VERSION=v0.4.44
RUN wget -qO- "https://github.com/rust-lang/mdBook/releases/download/${MDBOOK_VERSION}/mdbook-${MDBOOK_VERSION}-x86_64-unknown-linux-musl.tar.gz" \
    | tar xz -C /usr/local/bin
WORKDIR /docs
COPY docs/ .
RUN mdbook build

FROM nginx:alpine

COPY --from=build /app/dist /usr/share/nginx/html
COPY --from=docs-build /docs/book /usr/share/nginx/html/docs
COPY frontend/nginx.conf /etc/nginx/templates/default.conf.template

ENV API_UPSTREAM=http://backend:8000

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD wget -qO- http://localhost:80/ || exit 1

CMD ["/bin/sh", "-c", "envsubst '${API_UPSTREAM}' < /etc/nginx/templates/default.conf.template > /etc/nginx/conf.d/default.conf && nginx -g 'daemon off;'"]
