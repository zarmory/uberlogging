SHELL = /bin/bash

.PHONY: release
release:
	bump2version --verbose $${PART:-patch} --tag-message "Release {new_version}"
	git push
	git push --tags

.PHONY: test-docs
test-docs:
	./setup.py checkdocs

.PHONY: upload
upload: test-docs
	./setup.py sdist upload

.PHONY: restview
restview:
	restview README.rst -w README.rst

.PHONY: test-style
test-style:
	pre-commit run --all-files

.PHONY: test-python
test-python:
	./demo.sh

.PHONY: test
test: test-python test-style test-docs

bootstrap:
	echo "layout pipenv" > .envrc
	direnv allow
	pipenv install --dev
	pipenv run pip install -e .
	pipenv run pre-commit install
