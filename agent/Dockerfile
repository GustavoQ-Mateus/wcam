FROM node:24-slim AS web
WORKDIR /app/web
COPY web/package.json web/package-lock.json ./
RUN npm ci
COPY locales/ /app/locales/
COPY web/ ./
RUN npm run build

FROM python:3.13-slim
COPY --from=ghcr.io/astral-sh/uv:0.13.6 /uv /bin/uv
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy
WORKDIR /app/agent
COPY agent/pyproject.toml agent/uv.lock agent/README.md ./
RUN uv sync --frozen --no-dev --no-install-project
COPY agent/src/ ./src/
RUN uv sync --frozen --no-dev
COPY locales/ /app/locales/
COPY --from=web /app/web/dist/ /app/web/dist/
RUN useradd --create-home wcam
USER wcam
EXPOSE 8080 8443
CMD ["/app/agent/.venv/bin/wcam"]
