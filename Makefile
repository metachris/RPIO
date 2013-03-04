doc_upload: doc
	python setup.py upload_docs --upload-dir=documentation/build/html/

doc:
	cd documentation && make html
	cd source/scripts/man && make man
	cp source/scripts/man/build/man/rpio.1 source/scripts/man/

clean:
	rm -rf build dist RPIO.egg-info
	cd documentation && make clean
	cd source/scripts/man && make clean
