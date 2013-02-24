"""
Fabric makes it super easy to build and test the code on a Raspberry
(in this case, with just one command):

    $ fab test

You'll need to have Fabric installed ('$ sudo pip install fabric'),
SSH access to the Raspberry Pi, abd the right host in env.hosts.
"""
from fabric.api import run, local, cd, put, env


env.use_ssh_config = True
env.hosts = ["raspberry_dev"]


def upload():
    """
    Replaces /tmp/source with content of source/
    and rebuilds the C code
    """
    local("tar -czf /tmp/rpio.tar.gz source")
    run("rm -rf /tmp/rpio.tar.gz /tmp/source")
    put("/tmp/rpio.tar.gz", "/tmp/")
    with cd("/tmp"):
        run("tar -xf rpio.tar.gz")
    with cd("/tmp/source/c_gpio"):
        run("make")
        run("cp build/GPIO.so ../")
    print("Module built and ready to use in '/tmp/source/'.")


def upload_soft():
    """ Updates /tmp/source with content of source/ """
    local("tar -czf /tmp/rpio.tar.gz source")
    put("/tmp/rpio.tar.gz", "/tmp/")
    with cd("/tmp"):
        run("tar -xf rpio.tar.gz")


def upload_dist():
    """ Makes an sdist and uploads it to /tmp """
    local("python setup.py sdist")
    put("dist/*.tar.gz", "/tmp/")


def rpiotest():
    """ Uploads RPIO py and runs the RPIO test suite """
    upload_soft()
    with cd("/tmp/source"):
        run("sudo python run_tests.py")


def buildtest():
    """
    Uploads and builds the C code for both
    python2.7 and 3.2, and tests importing.
    """
    upload_soft()
    with cd("/tmp/source/c_gpio"):
        run("""echo "import GPIO\nprint(GPIO.VERSION_GPIO)" > test.py""")
        run("make gpio2.7 && cp build/GPIO.so .")
        run("sudo python2.7 test.py")
        run("make gpio3.2 && cp build/GPIO.so .")
        run("sudo python3.2 test.py")
    run("rm GPIO.so")
