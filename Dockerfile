# Runtime image for the theia-mcr command-line tool. The GUI is not included.
# Build: docker build -t theia-mcr-iq:dev .    Run: docker/theia-mcr <command>

FROM ghcr.io/astral-sh/uv:python3.13-alpine AS builder
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=0
WORKDIR /app

# Dependencies first so a source change does not invalidate this layer
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-install-project --no-dev

# --no-editable copies the package into the venv; /app/src does not exist in the runtime stage
COPY . .
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev --no-editable

FROM python:3.13-alpine
COPY --from=builder /app/.venv /app/.venv
# No pyproject in the image, so paths.data_dir() needs the explicit override
ENV PATH="/app/.venv/bin:$PATH" \
    THEIA_MCR_DATA_DIR=/data
VOLUME /data
ENTRYPOINT ["theia-mcr"]
CMD ["--help"]
