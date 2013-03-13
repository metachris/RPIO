# $Id: Makefile,v 1.0 2013/03/12 01:01:35 Chris Hager Exp $
#

all:
	@echo "make source - Create source package"
	@echo "make doc - Generate the html documentation"
	@echo "make doc_upload - make doc and upload to pythonhosted.com/RPIO"
	@echo "make clean - Clean up build directories"

source:
	$(PYTHON) setup.py sdist $(COMPILE)


clean:
	python setup.py clean
	find . -name '*.pyc' -delete
	rm -rf build dist MANIFEST Debug/ source/Debug RPIO.egg-info source/RPIO.egg-info
	cd documentation && make clean
	cd source/scripts/man && make clean

doc_upload: doc
	python setup.py upload_docs --upload-dir=documentation/build/html/

doc:
	cd documentation && make html
	cd source/scripts/man && make man
	cp source/scripts/man/build/man/rpio.1 source/scripts/man/
