SHELL = /bin/bash

release:
	bumpversion --verbose $${PART:-patch}
	git push
	git push --tags
