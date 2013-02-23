import os.path
import datetime

from fabric.api import run, local, cd, lcd, put, env, hosts, hide
from fabric.contrib.files import exists
from time import sleep

RPIO_VERSION = "0.6.4"

env.use_ssh_config = True
env.hosts = ["raspberry_dev"]
print("Uploading to %s" % env.hosts)


def test():
    local("python setup.py sdist")

    run("rm -rf /tmp/RPIO-%s*" % RPIO_VERSION)
    put("dist/RPIO-%s.tar.gz" % RPIO_VERSION, "/tmp/")
    with cd("/tmp"):
        run("tar -xvf RPIO-%s.tar.gz" % RPIO_VERSION)
    with cd("/tmp/RPIO-%s" % RPIO_VERSION):
        run("python setup.py build")
