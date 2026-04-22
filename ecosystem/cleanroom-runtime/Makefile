PYTHON ?= python3

.PHONY: install test smoke release-check clean

install:
	$(PYTHON) -m pip install -U pip
	$(PYTHON) -m pip install -e .[dev]

test:
	pytest -q

smoke:
	bash scripts/smoke.sh

release-check:
	bash scripts/release_check.sh

clean:
	find . -type d -name '__pycache__' -prune -exec rm -rf {} +
	rm -rf .pytest_cache .venv build dist *.egg-info src/*.egg-info
	rm -rf .arc_lucifer smoke.txt smoke_trace.html bench_smoke.txt release_backup.sqlite3 release_events.jsonl
