FROM node:24.11.1-bookworm-slim AS frontend
WORKDIR /build/client
COPY client/package.json client/package-lock.json ./
RUN npm ci
COPY client/ ./
RUN npm run build

FROM python:3.11.13-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /app
COPY requirements-platform*.txt ./
RUN pip install --no-cache-dir -r requirements-platform-m6.txt
RUN groupadd --gid 10001 maths && useradd --uid 10001 --gid maths --create-home maths \
    && mkdir -p /var/lib/maths/rag && chown -R maths:maths /var/lib/maths
COPY agent_platform/ agent_platform/
COPY --from=frontend /build/agent_platform/static/chat/ agent_platform/static/chat/
COPY reasoning_agent/ reasoning_agent/
COPY skill2_en/ skill2_en/
COPY skill2/ skill2/
COPY strategy_data/ strategy_data/
COPY deployment_bootstrap.py llm_client.py ./
USER maths
CMD ["python", "-m", "agent_platform.deployment", "api"]

FROM runtime AS rag
USER root
RUN pip install --no-cache-dir -r requirements-platform-m5.txt
USER maths
