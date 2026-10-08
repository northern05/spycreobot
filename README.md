# spycreobot

Use Python 3.10 for the pinned dependencies in `requirements.txt`. Python 3.14
cannot build several of these older native dependencies.

```bash
python3.10 -m venv .venv310
source .venv310/bin/activate
python -m pip install -r requirements.txt
python -m pip check
```

If `.venv310` already exists, activate it before installing dependencies. Select
`.venv310/bin/python` as the project interpreter in your IDE as well.

Backend tests use Python 3.10 and a temporary SQLite database; no running services
or credentials are required.

```bash
source .venv310/bin/activate
python -m pip install -r requirements-test.txt
python -m pytest
python -m pytest -m unit
python -m pytest -m integration
```

Unit tests mock persistence and cover identity lookup, creation, commit errors,
wallet updates, and initial credits. Integration tests exercise the auth router,
real SQLAlchemy persistence, repeat authentication, balance preservation, unique
wallet constraints, and request validation. Each test gets its own database.
Additional tests cover credits pricing and spending, payment processing and
deduplication, pins creation/listing/deletion, transactions, creative search,
filters, pagination, soft deletion, cache jobs, policies, GIF serving, and utility
functions. Wallet-driver integration tests use HTTPX's mock transport to check
response parsing, asset decimals, request parameters, and HTTP failures.

The test harness skips the eager `app` and `app.api` package initializers to avoid
starting unrelated services; it loads the real auth modules and router. It does
not cover the full application startup, Telegram bot handlers, or live external
services. SQLite tests use JSON variants for PostgreSQL ARRAY columns and enable
foreign-key constraints. PostgreSQL array filter SQL is checked by compilation;
executing those predicates still requires a PostgreSQL test database. External
Facebook and wallet responses are mocked; database and API logic execute normally.

The current auth endpoint identifies users by supplied Telegram ID or wallet;
it does not verify identity ownership or issue access/refresh tokens. These tests
cover the existing behavior. Empty requests and Telegram-only requests are not
validated by the schema and can fail the database's required-wallet constraint.
