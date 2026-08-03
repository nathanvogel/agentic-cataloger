FROM python:3.14.6-slim-trixie AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends libatomic1 \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir uv==0.12.1

COPY pyproject.toml uv.lock README.md ./
COPY src ./src
COPY migrations ./migrations
COPY alembic.ini ./

RUN uv sync --frozen --no-dev

ENV PATH="/app/.venv/bin:$PATH"

ENTRYPOINT ["agentic-cataloger"]
CMD ["api"]

# Devcontainer only — Node (corepack/yarn) + shell tooling. Prod roles use `base`.
FROM base AS dev

ARG NODE_VERSION=25.2.1
ARG TARGETARCH
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
        fd-find \
        git \
        git-lfs \
        openssh-client \
        postgresql-client \
        ripgrep \
        xz-utils \
    && case "${TARGETARCH}" in \
        amd64) NODE_ARCH=linux-x64 ;; \
        arm64) NODE_ARCH=linux-arm64 ;; \
        *) echo "unsupported arch: ${TARGETARCH}" && exit 1 ;; \
    esac \
    && curl -fsSL "https://nodejs.org/dist/v${NODE_VERSION}/node-v${NODE_VERSION}-${NODE_ARCH}.tar.xz" \
    | tar -xJ -C /usr/local --strip-components=1 \
    && npm install -g corepack \
    && corepack enable \
    && COREPACK_ENABLE_DOWNLOAD_PROMPT=0 corepack prepare yarn@4.11.0 --activate \
    && ln -sf "$(command -v fdfind)" /usr/local/bin/fd \
    && git lfs install --system \
    && rm -rf /var/lib/apt/lists/*

ARG CLAUDE_CODE_VERSION=2.1.220
RUN curl -fsSL https://claude.ai/install.sh | bash -s "${CLAUDE_CODE_VERSION}"

ARG RTK_VERSION=v0.44.2
RUN RTK_VERSION="${RTK_VERSION}" \
    curl -fsSL https://raw.githubusercontent.com/rtk-ai/rtk/refs/heads/master/install.sh | sh

ENV COREPACK_ENABLE_DOWNLOAD_PROMPT=0 \
    PATH="/root/.local/bin:${PATH}"
