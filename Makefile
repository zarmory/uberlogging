SHELL = /bin/bash

.PHONY: release
release:
	bumpversion --verbose $${PART:-patch}
	git push
	git push --tags


.PHONY: doc-check
doc-check:
	./setup.py checkdocs

upload: doc-check
	./setup.py sdist upload
