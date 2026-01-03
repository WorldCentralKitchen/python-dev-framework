.PHONY: setup-ide test lint format

# IDE setup - creates .vscode/settings.json and extensions.json
setup-ide:
	uv run python scripts/setup_ide.py

# Run tests
test:
	uv run pytest

# Run linting
lint:
	uv run ruff check .
	uv run mypy hooks/scripts

# Format code
format:
	uv run ruff format .
	uv run ruff check --fix .
