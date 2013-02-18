rm -rf build dist RPIO.egg-info

python2.6 setup.py bdist_egg upload
python2.7 setup.py bdist_egg upload
python3.2 setup.py bdist_egg upload

python2.7 setup.py sdist upload
