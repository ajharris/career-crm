# Installation

## Docker (recommended)

1. Copy `.env.example` to `.env` and replace every placeholder secret.
2. Run `docker compose up --build -d`.
3. Open `http://localhost:5000`, register, and complete onboarding.

Compose runs PostgreSQL, applies Alembic migrations, and starts Gunicorn. Uploaded documents and database data live in named volumes.

## Local development

Create a Python 3.12+ virtual environment, install `requirements-dev.txt`, configure `DATABASE_URL`, then run:

```sh
flask db upgrade
flask run --debug
```

SQLite remains supported for tests and quick local evaluation. PostgreSQL is the production target.
