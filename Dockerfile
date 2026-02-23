FROM python:3.14-slim-trixie AS build

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /package

COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

COPY pyproject.toml uv.lock ./

RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-project --no-editable --no-dev

COPY app ./app

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-editable --no-dev && \
    # Fix kopf path
    sed -i "1s/\/package//" /package/.venv/bin/kopf

FROM python:3.14-slim-trixie AS app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/.venv/bin:${PATH}" \
    PYTHONPATH="/"

RUN groupadd -r kube-up && \
    useradd -r -g kube-up kube-up

COPY --from=build /package/ /

USER kube-up

EXPOSE 8080
