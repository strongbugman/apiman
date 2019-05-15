all: test

version=`python -c 'import apiman; print(apiman.__version__)'`

test:
	black apiman tests setup.py --check
	flake8 apiman tests setup.py
	mypy --ignore-missing-imports apiman
	python setup.py pytest

black:
	black apiman tests setup.py

tag:
	git tag $(version) -m "Release of version $(version)"

sdist:
	./setup.py sdist

pypi_release: clean
	./setup.py sdist && twine upload dist/*

github_release:
	git push origin --tags && git push

release: tag github_release pypi_release

clean:
	rm -rf .eggs *.egg-info dist build
