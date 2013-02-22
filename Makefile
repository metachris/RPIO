rpio:
	python2.7 setup.py sdist

doc_upload: doc
	python setup.py upload_docs --upload-dir=documentation/build/html/

doc:
	cd documentation && make html man
	cp documentation/build/man/rpio.1 documentation/

doctest:
	cp documentation/source/index.rst README.txt
	sed -i '' "1,8d" README.txt
	sed -i '' "s/:ref:\`*/**/g" README.txt
	sed -i '' "s/ <ref-.*>\`/**/g" README.txt
	sed -i '' "s/[.][.] _.*//g" README.txt
	sed -i '' "s/[:][:].*//g" README.txt

	cp README.txt README.md
	sed -i '' '1N;N;/^\n\n$/d;P;D' README.md

clean:
	rm -rf build dist RPIO.egg-info

