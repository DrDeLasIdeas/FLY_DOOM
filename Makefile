PYTHON ?= $(shell if [ -x .venv311/bin/python ]; then echo .venv311/bin/python; else echo python3; fi)

.PHONY: connectome test up down mac-setup demo stop restart status train verify fullscreen open

mac-setup:
	chmod +x scripts/setup_mac.sh
	./scripts/setup_mac.sh

connectome:
	$(PYTHON) scripts/generate_connectome_graph.py

test: connectome
	PYTHONPATH=. $(PYTHON) -m pytest tests/ -v

up:
	docker compose up --build

down:
	docker compose down

demo:
	chmod +x scripts/neurodoom.sh
	./scripts/neurodoom.sh start

stop:
	./scripts/neurodoom.sh stop

restart:
	./scripts/neurodoom.sh restart

status:
	./scripts/neurodoom.sh status

train:
	./scripts/neurodoom.sh train $(if $(PRESET),$(PRESET),fast)

verify:
	./scripts/neurodoom.sh verify

fullscreen:
	./scripts/neurodoom.sh fullscreen

open:
	./scripts/neurodoom.sh open
