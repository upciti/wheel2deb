MAKE := $(MAKE) --no-print-directory
SHELL = bash

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
	@echo

bdist:
	@python3 setup.py bdist_wheel

images: bdist
	@cp docker/dh-autoreconf_* dist/
	$(call map,build_debian_image,$(DEBIAN_DISTS))

check:
	@flake8 src

tests: bdist
	$(eval images := $(foreach a,$(DEBIAN_DISTS),wheel2deb:$(a)))
	$(call map,run_tests,$(images))

publish:
	$(foreach a,$(DEBIAN_DISTS),\
		docker tag wheel2deb:$(a) parkoview/wheel2deb:$(a);)
	@docker push parkoview/wheel2deb

clean:
	@rm -Rf src/*.egg-info .pytest_cache .cache .coverage .tox build dist docs/build htmlcov
	@find -depth -type d -name __pycache__ -exec rm -Rf {} \;
	@find -type f -name '*.pyc' -delete

.PHONY: default bdist images clean

define build_debian_image
	cat docker/Dockerfile.in | sed s/_IMAGE_/debian:$(1)-slim/ | docker build -f - -t wheel2deb:$(1) dist;
endef

define run_tests
	docker run -ti -v $(CURDIR):/data --entrypoint "" $(1) /bin/bash -c " \
		pip install dist/*.whl \
		&& rm -rf testing/__pycache__ \
		&& py.test --cov";
endef
