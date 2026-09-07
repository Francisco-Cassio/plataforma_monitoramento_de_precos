FROM python:3.12-slim

# Copia o binário oficial do uv para dentro do container
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app/src \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

# Copia apenas as definições de dependência primeiro
COPY pyproject.toml uv.lock ./

# Instala as dependências (sem instalar o código da aplicação ainda)
RUN uv sync --frozen --no-install-project --no-dev

# Código-fonte e migrações
COPY alembic.ini ./
COPY alembic ./alembic
COPY src ./src

# Coloca o virtualenv do uv no PATH do sistema
ENV PATH="/app/.venv/bin:$PATH"

# Comando padrão
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]