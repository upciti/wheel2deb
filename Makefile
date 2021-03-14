MAKE := $(MAKE) --no-print-directory
SHELL = sh

IMAGE_NAME ?= wheel2deb

default:
	@echo "Makefile for wheel2deb"
	@echo
	@echo 'Usage:'
	@echo
	@echo '    make check      check coding style (PEP-8, PEP-257)'
	@echo '    make bdist      build python wheel'
	@echo '    make image      build docker images'
	@echo '    make clean      cleanup all temporary files'
	@echo '    make tests      run pytest in docker image'
	@echo '    make publish    push release to pypi'
	@echo

bdist:
	@rm -f dist/*.whl
	@python3 setup.py bdist_wheel

image:
	@docker build -t wheel2deb .

check:
	@flake8 src

tests: image
	@docker run -v $(CURDIR):/data --entrypoint "" wheel2deb py.test --cov

publish: clean bdist
	twine upload dist/*.whl

clean:
	@rm -Rf src/*.egg-info .pytest_cache .cache .coverage .tox build dist docs/build htmlcov
	@find -depth -type d -name __pycache__ -exec rm -Rf {} \;
	@find -type f -name '*.pyc' -delete

.PHONY: default bdist images clean publish check
