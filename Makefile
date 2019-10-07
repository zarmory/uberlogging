SHELL = /bin/bash

.PHONY: release
release:
	bumpversion --verbose $${PART:-patch}
	git push
	git push --tags

.PHONY: doc-check
doc-check:
	./setup.py checkdocs

.PHONY: upload
upload: doc-check
	./setup.py sdist upload

.PHONY: restview
restview:
	restview README.rst -w README.rst

.PHONY: test
test: doc-check
	flake8 *.py */*.py
	isort --check *.py */*.py
