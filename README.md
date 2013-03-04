RPIO is an advanced GPIO module for the Raspberry Pi.

* Hardware PWM
* GPIO Input and Output (drop-in replacement for [RPi.GPIO](http://pypi.python.org/pypi/RPi.GPIO))
* GPIO Interrupts (callbacks when events occur on input gpios)
* TCP Socket Interrupts (callbacks when tcp socket clients send data)
* Well documented, tested, fast source code
* Minimal CPU and memory profile
* Open source (GPLv3+)


**[Visit pythonhosted.org/RPIO for the full documentation.](http://pythonhosted.org/RPIO)**


Installation
------------

The easiest way to install/update RPIO on a Raspberry Pi is with either ``easy_install`` or ``pip``::

    $ sudo apt-get install python-setuptools
    $ sudo easy_install -U RPIO
After the installation you can use ``import RPIO`` as well as the command-line tools ``rpio`` and ``rpio-curses``.


Feedback
--------

Please send feedback and ideas to chris@linuxuser.at, and [open an issue at Github](https://github.com/metachris/RPIO/issues/new)
if you've encountered a bug.


License
-------

    RPIO is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    RPIO is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.


Links
-----

* http://pythonhosted.org/RPIO
* http://pypi.python.org/pypi/RPIO
* http://pypi.python.org/pypi/RPi.GPIO
* http://www.raspberrypi.org/wp-content/uploads/2012/02/BCM2835-ARM-Peripherals.pdf
* http://www.kernel.org/doc/Documentation/gpio.txt
