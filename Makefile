MAKE := $(MAKE) --no-print-directory
SHELL = bash

default:
	@echo "Makefile for wheel2deb"
	@echo
	@echo 'Usage:'
	@echo
	@echo '    make check      check coding style (PEP-8, PEP-257)'
	@echo '    make bdist      build python wheel'
	@echo '    make images     build docker images'
	@echo '    make clean      cleanup all temporary files'
	@echo

bdist:
	@python3 setup.py bdist_wheel

images: bdist
	@cp docker/dh-autoreconf_* dist/
	$(call build_image,debian:jessie-slim,jessie)
	$(call build_image,debian:stretch-slim,stretch)
	$(call build_image,debian:buster-slim,buster)

check:
	@flake8 src

test:
	$(call run_tests,wheel2deb:jessie)
	$(call run_tests,wheel2deb:stretch)
	$(call run_tests,wheel2deb:buster)

clean:
	@rm -Rf src/*.egg-info .pytest_cache .cache .coverage .tox build dist docs/build htmlcov
	@find -depth -type d -name __pycache__ -exec rm -Rf {} \;
	@find -type f -name '*.pyc' -delete

.PHONY: default bdist images clean

define build_image
	@cat docker/Dockerfile.in | sed s/_IMAGE_/$(1)/ | docker build -f - -t wheel2deb:$(2) dist
endef

define run_tests
	@docker run -ti -v $(CURDIR):/data --entrypoint "" $(1) /bin/bash -c " \
		pip install -e . \
		&& mkdir /testing \
		&& cp -r testing/*.py /testing \
		&& cd /testing \
		&& py.test"
endef
