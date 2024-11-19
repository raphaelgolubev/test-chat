# Я взял многоэтапную сборку из другого своего репозитория 
# https://github.com/raphaelgolubev/hola-api-register-ms/blob/75bce904eda65789482b0dc155cc6f5fbcb7bb92/Dockerfile

# =================================== base
FROM python:3.13.0-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Указываем рабочую директорию
WORKDIR /app

# =================================== builder
FROM base AS builder

ENV PIP_DEFAULT_TIMEOUT=100 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    POETRY_VERSION=1.8.3 \
    POETRY_HOME=/opt/poetry \
    POETRY_VENV=/opt/poetry-venv \
    POETRY_CACHE_DIR=/opt/.cache

# Копируем файлы poetry.lock и pyproject.toml для установки зависимостей
COPY pyproject.toml poetry.lock ./

# Устанавливаем Poetry
RUN python3 -m venv $POETRY_VENV \
    && $POETRY_VENV/bin/pip install -U pip setuptools \
    && $POETRY_VENV/bin/pip install poetry==${POETRY_VERSION} \
    && $POETRY_VENV/bin/poetry config virtualenvs.create false \
    && $POETRY_VENV/bin/poetry install --no-dev --no-interaction --no-ansi

# =================================== final
FROM builder AS final

# Прописываем путь до Poetry в PATH
ENV PATH="${PATH}:${POETRY_VENV}/bin"

# Копируем виртуальное окружение в контейнер
COPY --from=builder $POETRY_VENV $POETRY_VENV

# Копируем проект в контейнер
COPY . .

# Указываем команду для запуска приложения
CMD [ "poetry", "run", "python", "." ]