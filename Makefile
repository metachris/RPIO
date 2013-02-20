all: rpio

rpio:
	python2.7 setup.py sdist

clean:
	rm -rf build dist RPIO.egg-info

