.PHONY: api-test api-lint web-install web-lint contracts-test fixtures

api-test:
	cd apps/api && uv run pytest

api-lint:
	cd apps/api && uv run ruff check app tests ../../knowledge/scripts

fixtures:
	cd apps/api && PYTHONPATH=../..:. uv run python ../../knowledge/scripts/generate_synthetic_data.py

web-install:
	cd apps/web && pnpm install

web-lint:
	cd apps/web && pnpm lint

contracts-test:
	cd contracts && npm test

