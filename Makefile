.PHONY: install test lint typecheck build

install:
	python -m pip install -e ".[dev]"

test:
	pytest

lint:
	ruff check src tests
	black --check src tests

typecheck:
	python -m py_compile src/netbox_mcp/*.py

build:
	docker build -t ghcr.io/basalto/netbox-mcp-server:latest .
