# Troubleshooting

## Settings fields are missing

Run commands that load application settings from the repository root or from
`apps/api`. Scripts that live outside `apps/api` explicitly read
`apps/api/.env`.

## Alembic says tables already exist

Older development runs may have created tables with `database/seed_pg.py`.
After confirming the schema exists, mark the database once:

```bash
cd apps/api
uv run alembic stamp head
```

Fresh databases should use `uv run alembic upgrade head`.

## Environment check blocks KeeperHub

This is expected until both `KEEPERHUB_API_KEY` and `KEEPERHUB_WALLET_ADDRESS`
are set. Do not bypass this for a live demo.

## Web lint is interactive

The current Next.js lint script may ask to configure ESLint. Use TypeScript
checking as the non-interactive gate until the web lint configuration is added:

```bash
cd apps/web
npm exec -- tsc --noEmit
```
