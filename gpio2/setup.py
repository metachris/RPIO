import os
from setuptools import setup

# Utility function to read the README file.
# Used for the long_description.  It's nice, because now 1) we have a top level
# README file and 2) it's easier to type in the README file than to put a raw
# string in below ...
def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

setup(
    #install_requires=['RPi.GPIO'],
    name="RPi.GPIO2",
    packages=['GPIO2'],
    version="0.2",
    description="An extension for RPi.GPIO to easily use interrupts on the Raspberry Pi",
    long_description=read('README.md'),
    url="https://github.com/metachris/raspberrypi-utils",

    author="Chris Hager",
    author_email="chris@linuxuser.at",

    license="MIT",
    keywords=["raspberry", "raspberry pi", "interrupts", "gpio", "gpio2"],
    classifiers=[
        "Development Status :: 4 - Beta",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Operating System :: POSIX :: Linux",
        "Topic :: Utilities",
        "Topic :: Software Development",
        "Topic :: Home Automation",
        "Topic :: System :: Hardware"
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
    ],
)
