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

install-agent-skill:
	@target="$${CODEX_HOME:-$$HOME/.codex}/skills/omx-agent"; \
	mkdir -p "$$target"; \
	cp skills/omx-agent/SKILL.md "$$target/SKILL.md"; \
	printf 'installed %s\n' "$$target/SKILL.md"

verify-agent-skill:
	@target="$${CODEX_HOME:-$$HOME/.codex}/skills/omx-agent/SKILL.md"; \
	test -f "$$target"; \
	cmp -s skills/omx-agent/SKILL.md "$$target"; \
	printf 'agent skill synchronized: %s\n' "$$target"
