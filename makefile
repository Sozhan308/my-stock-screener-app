.PHONY: install lint format format-check test check fix scan-daily scan-4h update


install:
	uv sync --dev


lint:
	uv run ruff check .


format:
	uv run ruff format .


format-check:
	uv run ruff format --check .


test:
	uv run pytest


check:
	uv run ruff check .
	uv run ruff format --check .
	uv run pytest


fix:
	uv run ruff check --fix .
	uv run ruff format .
	uv run pytest


scan-daily:
	uv run minervini scan --timeframe daily


scan-4h:
	uv run minervini scan --timeframe 4h


update:
	uv run minervini update