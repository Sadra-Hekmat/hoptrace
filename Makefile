.PHONY: help test run install clean

help:
	@echo "make test     Run the standard-library test suite"
	@echo "make run      Run the healthy scenario"
	@echo "make install  Install to ~/.local/bin"


test:
	PYTHONPATH=src python3 -m unittest discover -s tests -v

run:
	./packet-odyssey run --scenario successful-https --no-history

install:
	./install.sh

clean:
	rm -rf build dist *.egg-info src/*.egg-info
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
