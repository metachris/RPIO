"""
Fabric makes it super easy to build and test the code on a Raspberry.
You can see all commands with `$ fab -l`. Typical usages:

    $ fab upload build test
    $ fab upload test

You'll need to have Fabric installed ('$ sudo pip install fabric'),
SSH access to the Raspberry Pi, abd the right host in env.hosts.
"""
from fabric.api import run, local, cd, put, env
from fabric.operations import prompt

env.use_ssh_config = True

# Set default hosts
if not env.hosts:
    env.hosts = ["raspberry_dev_local"]


def clean():
    run("rm -rf /tmp/source/")


def upload():
    """ Uploads source/ to raspberrypi:/tmp/source/ """
    local("tar -czf /tmp/rpio.tar.gz source")
    put("/tmp/rpio.tar.gz", "/tmp/")
    with cd("/tmp"):
        run("tar -xf rpio.tar.gz")
        run("cp source/scripts/rpio source/")


def upload_dist():
    """ Makes an sdist and uploads it to /tmp """
    local("python setup.py sdist")
    put("dist/*.tar.gz", "/tmp/")


def test_pwm():
    upload()
    with cd("/tmp/source/c_pwm"):
        run("make dirty")
        run("sudo ./pwm")


def build():
    """ Builds source with Python 2.7 and 3.2, and tests import """
    with cd("/tmp/source/c_gpio"):
        run("""echo "import GPIO\nprint(GPIO.VERSION_GPIO)" > test.py""")
        run("make gpio2.7 && cp build/GPIO.so .")
        run("sudo python2.7 test.py")
        run("cp GPIO.so ../RPIO/")
        run("cp GPIO.so ../RPIO/GPIO27.so")
        run("make gpio3.2 && cp build/GPIO.so .")
        run("sudo python3.2 test.py")
        run("mv GPIO.so ../RPIO/GPIO32.so")


def test():
    """ Invokes test suite in `run_tests.py` """
    with cd("/tmp/source/RPIO"):
        run("cp GPIO27.so GPIO.so")
    with cd("/tmp/source"):
        run("sudo python run_tests.py")


def test3():
    """ Invokes test suite in `run_tests.py` """
    with cd("/tmp/source/RPIO"):
        run("cp GPIO32.so GPIO.so")
    with cd("/tmp/source"):
        run("sudo python3 run_tests.py")


def upload_to_pypi():
    """ Upload sdist and bdist_eggs to pypi """
    # DO_UPLOAD provides a safety mechanism to avoid accidental pushes to pypi.
    # Set it to "upload" to actually push to pypi; else it only does a dry-run.
    DO_UPLOAD = ""  # "upload"

    # One more safety input and then we are ready to go :)
    x = prompt("Are you sure to upload the current version to pypi?")
    if not x or not x.lower() in ["y", "yes"]:
        print("Error: no build found in dist/")
        return

    local("rm -rf dist")
    local("python setup.py sdist %s" % DO_UPLOAD)
    fn = local("ls dist/", capture=True)
    version = fn[5:-7]
    put("dist/%s" % fn, "/tmp/")
    with cd("/tmp"):
        run("tar -xf /tmp/%s" % fn)
    with cd("/tmp/RPIO-%s" % version):
        run("python2.6 setup.py bdist_egg %s" % DO_UPLOAD)
        run("python2.7 setup.py bdist_egg %s" % DO_UPLOAD)
        run("python3.2 setup.py bdist_egg %s" % DO_UPLOAD)
