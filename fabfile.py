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


def test():
    local("tar -czf /tmp/rpio.tar.gz source")
    run("rm -rf /tmp/rpio.tar.gz source")
    put("/tmp/rpio.tar.gz", "/tmp/")
    with cd("/tmp"):
        run("tar -xf rpio.tar.gz")
    with cd("/tmp/source/c_gpio"):
        run("make")
        run("cp build/GPIO.so ../")
    print("Module built and ready to use in '/tmp/source/'.")


def test_dist():
    local("python setup.py sdist")
    put("dist/*.tar.gz", "/tmp/")
