rpio:
	python2.7 setup.py sdist

doc_upload: doc
	python setup.py upload_docs --upload-dir=documentation/build/html/

doc:
	cd documentation && make html man
	cp documentation/build/man/rpio.1 documentation/

	# Make reST version for pypi
	echo "**Visit http://pythonhosted.org/RPIO for a pretty version of this documentation.**\n" > README.txt
	cat documentation/source/index.rst >> README.txt
	sed -i '' "3,10d" README.txt
	sed -i '' "s/:ref:\`*/**/g" README.txt
	sed -i '' "s/ <ref-.*>\`/**/g" README.txt
	sed -i '' "s/[.][.] _.*//g" README.txt

 	# Make markdown version for Github
	cp README.txt README.md
	sed -i '' "s/^:://g" README.md
	sed -i '' "s/::/:/g" README.md

clean:
	rm -rf build dist RPIO.egg-info
	cd documentation && make clean
