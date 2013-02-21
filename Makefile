rpio:
	python2.7 setup.py sdist

doc_upload: doc
	python setup.py upload_docs --upload-dir=documentation/build/html/

doc:
	cd documentation && make html man
	cp documentation/build/man/rpio.1 documentation/

clean:
	rm -rf build dist RPIO.egg-info

