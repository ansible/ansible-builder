PYTHON ?= python
ifeq ($(origin VIRTUAL_ENV), undefined)
    DIST_PYTHON ?= poetry run $(PYTHON)
else
    DIST_PYTHON ?= $(PYTHON)
endif

CONTAINER_ENGINE ?= docker

NAME = ansible-builder
IMAGE_NAME ?= quay.io/ansible/ansible-builder
PIP_NAME = ansible_builder
VERSION := $(shell git describe --tags)
ifeq ($(OFFICIAL),yes)
    RELEASE ?= 1
else
    ifeq ($(origin RELEASE), undefined)
        RELEASE := 0.git$(shell date -u +%Y%m%d%H).$(shell git rev-parse --short HEAD)
    endif
endif

# RPM build variables
MOCK_BIN ?= mock
MOCK_CONFIG ?= epel-7-x86_64

RPM_NVR = $(NAME)-$(VERSION)-$(RELEASE)$(RPM_DIST)
RPM_DIST ?= $(shell rpm --eval '%{?dist}' 2>/dev/null)
RPM_ARCH ?= $(shell rpm --eval '%{_arch}' 2>/dev/null)

# Provide a fallback value for RPM_ARCH
ifeq ($(RPM_ARCH),)
    RPM_ARCH = $(shell uname -m)
endif

.PHONY: clean dist sdist dev shell rpm srpm test

clean:
	rm -rf dist
	rm -rf build
	rm -rf ansible-builder.egg-info
	rm -rf rpm-build
	rm -rf docs/_build/
	find . -type f -regex ".*\py[co]$$" -delete
	rm -rf $(shell find test/ -type d -name "artifacts")

dist:
	poetry build

sdist: dist/$(NAME)-$(VERSION).tar.gz

# Generate setup.py transiently for the sdist so we don't have to deal with
# packaging poetry as a RPM for rpm build time dependencies.
dist/$(NAME)-$(VERSION).tar.gz:
	tox -e version
	$(DIST_PYTHON) setup.py sdist

# Used to make image for running tests
image:
	python setup.py sdist
	$(CONTAINER_ENGINE) build --rm=true -t $(IMAGE_NAME) -f Containerfile .
	$(CONTAINER_ENGINE) tag $(IMAGE_NAME) $(IMAGE_NAME):$(VERSION)

dev:
	poetry install

shell:
	poetry shell

test:
	@tox

docs/_build:
	cd docs && make html

docs: docs/_build

rpm:
	MOCK_CONFIG=$(MOCK_CONFIG) docker-compose -f packaging/rpm/docker-compose.yml build
	MOCK_CONFIG=$(MOCK_CONFIG) docker-compose -f packaging/rpm/docker-compose.yml \
	  run --rm -e RELEASE=$(RELEASE) rpm-builder "make mock-rpm"

srpm:
	MOCK_CONFIG=$(MOCK_CONFIG) docker-compose -f packaging/rpm/docker-compose.yml build
	MOCK_CONFIG=$(MOCK_CONFIG) docker-compose -f packaging/rpm/docker-compose.yml \
	  run --rm -e RELEASE=$(RELEASE) rpm-builder "make mock-srpm"

mock-rpm: rpm-build/$(RPM_NVR).$(RPM_ARCH).rpm

rpm-build/$(RPM_NVR).$(RPM_ARCH).rpm: rpm-build/$(RPM_NVR).src.rpm
	$(MOCK_BIN) -r $(MOCK_CONFIG) --arch=noarch \
	  --resultdir=rpm-build \
	  --rebuild rpm-build/$(RPM_NVR).src.rpm

mock-srpm: rpm-build/$(RPM_NVR).src.rpm

rpm-build/$(RPM_NVR).src.rpm: dist/$(NAME)-$(VERSION).tar.gz rpm-build rpm-build/$(NAME).spec
	$(MOCK_BIN) -r $(MOCK_CONFIG) --arch=noarch \
	  --resultdir=rpm-build \
	  --spec=rpm-build/$(NAME).spec \
	  --sources=rpm-build \
	  --buildsrpm

rpm-build/$(NAME).spec:
	ansible -c local -i localhost, all \
	    -m template \
	    -a "src=packaging/rpm/$(NAME).spec.j2 dest=rpm-build/$(NAME).spec" \
	    -e version=$(VERSION) \
	    -e release=$(RELEASE)

rpm-build: sdist
	mkdir -p $@
	cp dist/$(NAME)-$(VERSION).tar.gz rpm-build/$(NAME)-$(VERSION)-$(RELEASE).tar.gz

print-%:
	@echo $($*)
