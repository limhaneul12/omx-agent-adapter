install:
	uv sync --frozen --all-groups

ruff:
	uv run ruff check .

pyrefly:
	uv run pyrefly check src

test:
	uv run pytest -q

ci: ruff pyrefly test
