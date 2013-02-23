import os
from setuptools import setup, Extension


def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()


setup(
    name="RPIO",
    version="0.7.1",
    package_dir={"": "source"},
    py_modules=["RPIO"],
    ext_modules=[Extension('GPIO', ['source/c_gpio/py_gpio.c', \
            'source/c_gpio/c_gpio.c', 'source/c_gpio/cpuinfo.c'])],
    scripts=["source/rpio"],

    description=(("GPIO toolbox for the Raspberry Pi. Extends RPi.GPIO "
            "with interrups, a command line tool and more")),
    long_description=read('README.rst'),
    url="https://github.com/metachris/RPIO",

    author="Chris Hager",
    author_email="chris@linuxuser.at",

    license="MIT",
    keywords=["raspberry", "raspberry pi", "interrupts", "gpio", "rpio"],
    classifiers=[
        "Development Status :: 4 - Beta",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Operating System :: POSIX :: Linux",
        "Topic :: Utilities",
        "Topic :: Software Development",
        "Topic :: Home Automation",
        "Topic :: System :: Hardware",
        "Intended Audience :: Developers",
        ("License :: OSI Approved :: "
                "GNU General Public License v3 or later (GPLv3+)"),
        "License :: Other/Proprietary License",
    ],
)
