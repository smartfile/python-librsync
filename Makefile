test:
	# For testing non-Django projects.
	python test.py

verify:
	pyflakes -x W librsync
	pep8 --exclude=migrations --ignore=E501,E225 librsync

install:
	python setup.py install

publish:
	python setup.py register
	python setup.py sdist upload
