# Stage 1: Builder
FROM python:3.12-slim AS builder

WORKDIR /build

COPY pyproject.toml README.md ./
COPY src/ src/

RUN pip install --no-cache-dir build \
    && python -m build --wheel \
    && pip install --no-cache-dir --prefix=/install dist/*.whl

# Stage 2: Runtime
FROM python:3.12-slim

LABEL org.opencontainers.image.source="https://github.com/Ghostwritten/kubeagent"
LABEL org.opencontainers.image.description="Natural language CLI for Kubernetes cluster management"
LABEL org.opencontainers.image.licenses="MIT"

COPY --from=builder /install /usr/local

# Create non-root user
RUN useradd --create-home kubeagent
USER kubeagent
WORKDIR /home/kubeagent

ENTRYPOINT ["kubeagent"]
