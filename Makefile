install:
	uv sync --frozen --all-groups

ruff:
	uv run ruff format --check .
	uv run ruff check .

pyrefly:
	uv run pyrefly check src/comx_harness

test:
	uv run pytest -q

native-test:
	uv run pytest -q -m native --override-ini="addopts=--strict-markers"

build:
	uv build

ci: ruff pyrefly test build
