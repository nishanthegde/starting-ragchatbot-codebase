.PHONY: format format-check lint test quality hooks-install hooks-run

format:
	uv run black .
	uv run ruff check . --fix

format-check:
	uv run black --check .
	uv run ruff check .

lint:
	uv run ruff check .

test:
	uv run pytest

quality: format-check test

hooks-install:
	uv run pre-commit install

hooks-run:
	uv run pre-commit run --all-files
