from fabric.api import run, local, cd, lcd, put, env, hosts, hide
from fabric.contrib.files import exists


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
