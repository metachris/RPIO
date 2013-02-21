all: rpio

rpio:
	python2.7 setup.py sdist

upload_docs:
	cd documentation
	make html
	cd ..
	python setup.py upload_docs --upload-dir=documentation/build/html/

clean:
	rm -rf build dist RPIO.egg-info

