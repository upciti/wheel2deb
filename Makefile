MAKE := $(MAKE) --no-print-directory
SHELL = sh

IMAGE_NAME ?= parkoview/wheel2deb

DEBIAN_DISTS := jessie stretch buster

map = $(foreach a,$(2),$(call $(1),$(a)))

default:
	@echo "Makefile for wheel2deb"
	@echo
	@echo 'Usage:'
	@echo
	@echo '    make check      check coding style (PEP-8, PEP-257)'
	@echo '    make bdist      build python wheel'
	@echo '    make images     build docker images'
	@echo '    make clean      cleanup all temporary files'
	@echo '    make tests      run pytest in docker images'
	@echo '    make publish    push release to pypi'
	@echo

bdist:
	@rm -f dist/*.whl
	@python3 setup.py bdist_wheel

images:
	@docker build -t debian:jessie-slim ./docker/patch-jessie
	@cp docker/dh-autoreconf_* dist/
	$(call map,build_debian_image,$(DEBIAN_DISTS))

check:
	@flake8 src

tests:
	$(eval images := $(foreach a,$(DEBIAN_DISTS),$(IMAGE_NAME):$(a)))
	$(call map,run_tests,$(images))

publish: clean bdist
	twine upload dist/*.whl

clean:
	@rm -Rf src/*.egg-info .pytest_cache .cache .coverage .tox build dist docs/build htmlcov
	@find -depth -type d -name __pycache__ -exec rm -Rf {} \;
	@find -type f -name '*.pyc' -delete

.PHONY: default bdist images clean publish check

define build_debian_image
	cat docker/Dockerfile.in | sed s/_IMAGE_/debian:$(1)-slim/ | docker build -t $(IMAGE_NAME):$(1) --cache-from $(IMAGE_NAME):$(1) -f - dist;
endef

define run_tests
	docker run -v $(CURDIR):/data --entrypoint "" $(1) /bin/sh -c " \
		pip install dist/*.whl \
		&& rm -rf testing/__pycache__ \
		&& py.test --cov"; \
	if (test $$? -ne 0); then exit 1; fi;
endef
