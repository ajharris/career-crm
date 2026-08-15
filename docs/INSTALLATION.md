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

To use instance-wide Google Drive document storage, enable the Google Drive API
in Google Cloud, create an OAuth 2.0 Web application, and set
`GOOGLE_DRIVE_CLIENT_ID`, `GOOGLE_DRIVE_CLIENT_SECRET`, and
`CREDENTIAL_ENCRYPTION_KEY`. Register
`https://<your-host>/settings/storage/callback/google-drive` as an authorized
redirect URI. An administrator can then connect the account from **Storage
Settings** in the account menu.

SQLite remains supported for tests and quick local evaluation. PostgreSQL is the production target.
