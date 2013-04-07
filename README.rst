RPIO is an advanced GPIO module for the Raspberry Pi.

* PWM via DMA (up to 1us resolution)
* GPIO input and output (drop-in replacement for `RPi.GPIO <http://pypi.python.org/pypi/RPi.GPIO>`_)
* GPIO interrupts (callbacks when events occur on input gpios)
* TCP socket interrupts (callbacks when tcp socket clients send data)
* Command-line tools ``rpio`` and ``rpio-curses``
* Well documented, fast source code with minimal CPU usage
* Open source (LGPLv3+)


`Visit pythonhosted.org/RPIO for the documentation. <http://pythonhosted.org/RPIO>`_


Installation
------------

The easiest way to install/update RPIO on a Raspberry Pi is with either ``easy_install`` or ``pip``::

    $ sudo apt-get install python-setuptools
    $ sudo easy_install -U RPIO

After the installation you can use ``import RPIO`` as well as the command-line tools ``rpio`` and ``rpio-curses``.

Debian packages are available at `metachris.github.com/rpio/download <http://metachris.github.com/rpio/download/latest/>`_.

An Arch Linux PKGBUILD is available at `aur.archlinux.org/packages/rpio <https://aur.archlinux.org/packages/rpio/>`_.


Examples
--------

You can find lots of examples inside the `documentation <http://pythonhosted.org/RPIO>`_, as well as in the `/examples/ source directory <https://github.com/metachris/RPIO/tree/master/examples>`_.


Feedback
--------

Please send feedback and ideas to chris@linuxuser.at, and `open an issue at Github <https://github.com/metachris/RPIO/issues/new>`_
if you've encountered a bug.


License
-------

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU Lesser General Public License as published
    by the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU Lesser General Public License for more details at
    <http://www.gnu.org/licenses/lgpl-3.0-standalone.html>


Copyright
---------

    Copyright (C) 2013 Chris Hager <chris@linuxuser.at>


Links
-----

* http://pythonhosted.org/RPIO
* http://pypi.python.org/pypi/RPIO
* http://pypi.python.org/pypi/RPi.GPIO
* http://www.raspberrypi.org/wp-content/uploads/2012/02/BCM2835-ARM-Peripherals.pdf
* http://www.kernel.org/doc/Documentation/gpio.txt
* `semver versioning standard <http://semver.org/>`_


Changes
-------

Please refer to the `'Changes' section in the documentation <http://pythonhosted.org/RPIO/#changes>`_.
