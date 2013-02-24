"""
Fabric makes it super easy to build and test the code on a Raspberry.
You can see all commands with `$ fab -l`. Typical usages:

    $ fab upload build test
    $ fab upload test

You'll need to have Fabric installed ('$ sudo pip install fabric'),
SSH access to the Raspberry Pi, abd the right host in env.hosts.
"""
from fabric.api import run, local, cd, put, env


env.use_ssh_config = True
env.hosts = ["raspberry_dev"]


def upload():
    """ Uploads source/ to raspberrypi:/tmp/source/ """
    local("tar -czf /tmp/rpio.tar.gz source")
    put("/tmp/rpio.tar.gz", "/tmp/")
    with cd("/tmp"):
        run("tar -xf rpio.tar.gz")


def upload_dist():
    """ Makes an sdist and uploads it to /tmp """
    local("python setup.py sdist")
    put("dist/*.tar.gz", "/tmp/")


def build():
    """ Builds source with Python 2.7 and 3.2, and tests import """
    with cd("/tmp/source/c_gpio"):
        run("""echo "import GPIO\nprint(GPIO.VERSION_GPIO)" > test.py""")
        run("make gpio2.7 && cp build/GPIO.so .")
        run("sudo python2.7 test.py")
        run("mv GPIO.so ../")   # keep new 2.7 version for rpiotests
        run("make gpio3.2 && cp build/GPIO.so .")
        run("sudo python3.2 test.py")
        run("rm GPIO.so")


def test():
    """ Invokes test suite in `run_tests.py` """
    with cd("/tmp/source"):
        run("sudo python run_tests.py")
