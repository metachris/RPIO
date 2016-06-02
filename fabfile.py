"""
You can see all commands with `$ fab -l`. Typical usages:

    $ fab upload build
    $ fab upload build_pwm
    $ fab upload test
    $ fab build_deb

"""
from fabric.api import run, local, cd, put, env
from fabric.operations import prompt, get

env.use_ssh_config = True

# Set default hosts
if not env.hosts:
    # env.hosts = ["raspberry_dev_local"]
    env.hosts = ["omxdev"]


def _get_cur_version():
    return local("bash version_update.sh --show", capture=True)


def clean():
    run("sudo rm -rf /tmp/source/")


def upload():
    """ Uploads source/ to raspberrypi:/tmp/source/ """
    local("tar -czf /tmp/rpio.tar.gz source")
    put("/tmp/rpio.tar.gz", "/tmp/")
    with cd("/tmp"):
        run("tar -xf rpio.tar.gz")
        run("cp source/scripts/rpio source/")
        run("cp source/scripts/rpio-curses source/")


def make_sdist():
    """ Makes an sdist package """
    local("python setup.py sdist")


def upload_sdist():
    """ Makes an sdist and uploads it to /tmp """
    make_sdist()
    put("dist/*.tar.gz", "/tmp/")


#
# Packaging
#
def build_rpm():
    pass
    # "python setup.py bdist_rpm
    # --post-install=rpm/postinstall --pre-uninstall=rpm/preuninstall"


def build_deb():
    v = _get_cur_version()

    run("rm -rf /tmp/RPIO*")
    run("rm -rf /tmp/build")
    run("mkdir /tmp/build")

    # Upload the sdist
    upload_sdist()
    with cd("/tmp/build"):
        run("tar -xvf /tmp/RPIO-%s.tar.gz" % v)
        run("mv RPIO-%s rpio-%s" % (v, v))

        run("mkdir rpio-%s/dist" % v)
        run("mv /tmp/RPIO-%s.tar.gz rpio-%s/dist/rpio_%s.orig.tar.gz" % \
                (v, v, v))

    # Upload debian/
    local("tar -czf /tmp/rpio_debian.tar.gz debian")
    put("/tmp/rpio_debian.tar.gz", "/tmp/")
    with cd("/tmp/build/rpio-%s" % v):
        run("tar -xvf /tmp/rpio_debian.tar.gz")
        run("dpkg-buildpackage -i -I -rfakeroot")


def grab_deb():
    # Custom github upload
    v = _get_cur_version()
    t = ("/Users/chris/Projects/private/web/metachris.github.com/"
            "rpio/download/%s/") % v
    local("mkdir -p %s" % t)
    get("/tmp/build/python-rpio_%s_armhf.deb" % v, t)
    get("/tmp/build/python3-rpio_%s_armhf.deb" % v, t)
    get("/tmp/build/rpio_*", t)
    print
    print "Debian release files copied. Do this now:"
    print ""
    print "    $ cd %s.." % t
    print "    $ ./gen_version_index.sh %s" % v
    print "    $ ./gen_index.sh %s" % v
    print "    $ git status"
    print "    $ git add ."
    print "    $ git commit -am 'Debian packages for RPIO %s" % v
    print "    $ git push"


#
# Building of GPIO and PWM C sources
#
def build_gpio():
    """ Builds source with Python 2.7 and 3.2, and tests import """
    with cd("/tmp/source/c_gpio"):
        test = "import _GPIO; print(_GPIO.VERSION_GPIO)"
        run("make gpio2.7 && cp build/_GPIO.so .")
        run('sudo python2.7 -c "%s"' % test)
        run("cp _GPIO.so ../RPIO/")
        run("cp _GPIO.so ../RPIO/_GPIO27.so")
        run("make gpio3.2 && cp build/_GPIO.so .")
        run('sudo python3.2 -c "%s"' % test)
        run("mv _GPIO.so ../RPIO/_GPIO32.so")


def build_pwm():
    """ Builds source with Python 2.7 and 3.2, and tests import """
    with cd("/tmp/source/c_pwm"):
        test = "import _PWM; print(_PWM.VERSION)"
        run("make py2.7")
        run('sudo python2.7 -c "%s"' % test)
        run("cp _PWM.so ../RPIO/PWM/")
        run("mv _PWM.so ../RPIO/PWM/_PWM27.so")
        run("make py3.2")
        run('python3.2 -c "%s"' % test)
        run("mv _PWM.so ../RPIO/PWM/_PWM32.so")


def build():
    build_gpio()
    build_pwm()


#
# Tests
#
def test_gpio():
    """ Invokes test suite in `run_tests.py` """
    with cd("/tmp/source/RPIO"):
        run("cp _GPIO27.so _GPIO.so")
    with cd("/tmp/source"):
        run("sudo python tests_gpio.py")


def test3_gpio():
    """ Invokes test suite in `run_tests.py` """
    with cd("/tmp/source/RPIO"):
        run("cp _GPIO32.so _GPIO.so")
    with cd("/tmp/source"):
        run("sudo python3 tests_gpio.py")
    with cd("/tmp/source/RPIO"):
        run("cp _GPIO27.so _GPIO.so")


def test_pwm():
    with cd("/tmp/source/RPIO"):
        run("cp _GPIO27.so _GPIO.so")
        run("cp PWM/_PWM27.so PWM/_PWM.so")
    with cd("/tmp/source"):
        run("sudo python tests_pwm.py")


def test3_pwm():
    with cd("/tmp/source/RPIO"):
        run("cp _GPIO32.so _GPIO.so")
        run("cp PWM/_PWM32.so PWM/_PWM.so")
    with cd("/tmp/source"):
        run("sudo python3 tests_pwm.py")
    with cd("/tmp/source/RPIO"):
        run("cp _GPIO27.so _GPIO.so")
        run("cp PWM/_PWM27.so PWM/_PWM.so")


#
# Other
#
def upload_to_pypi():
    """ Upload sdist and bdist_eggs to pypi """
    # One more safety input and then we are ready to go :)
    x = prompt("Are you sure to upload the current version to pypi?")
    if not x or not x.lower() in ["y", "yes"]:
        return

    local("rm -rf dist")
    local("python setup.py sdist")
    version = _get_cur_version()
    fn = "RPIO-%s.tar.gz" % version
    put("dist/%s" % fn, "/tmp/")
    with cd("/tmp"):
        run("tar -xf /tmp/%s" % fn)
    with cd("/tmp/RPIO-%s" % version):
        run("python2.6 setup.py bdist_egg upload")
        run("python2.7 setup.py bdist_egg upload")
        run("python3.2 setup.py bdist_egg upload")
    local("python setup.py sdist upload")
