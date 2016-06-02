Welcome to RPIO's documentation!
================================

RPIO is an advanced GPIO module for the Raspberry Pi.

* PWM via DMA (up to 1µs resolution)
* GPIO input and output (drop-in replacement for `RPi.GPIO <http://pypi.python.org/pypi/RPi.GPIO>`_)
* GPIO interrupts (callbacks when events occur on input gpios)
* TCP socket interrupts (callbacks when tcp socket clients send data)
* Command-line tools ``rpio`` and ``rpio-curses``
* Well documented, fast source code with minimal CPU usage
* Open source (LGPLv3+)

RPIO consists of two main components:

* :ref:`RPIO <ref-rpio-py>` -- Python modules which you can import in Python 2 or 3 with ``import RPIO``, ``import RPIO.PWM``, etc.
* :ref:`rpio <ref-rpio-cmd>` -- command-line tools for inspecting and manipulating GPIOs system-wide.


Documentation
-------------

.. toctree::
   :maxdepth: 2

   rpio_cmd
   rpio_py
   pwm_py


News
----

* v2.0.0-beta1: RPIO works with Raspberry Pi Zero, 2 and 3 (Thanks to Andy Baker and Reik Hua)
* v0.9.2: :ref:`PWM via DMA <ref-rpio-pwm-py>`
* v0.8.4: ``rpio-curses``
* v0.8.2: Socket server callbacks with :ref:`RPIO.add_tcp_callback(port, callback, threaded_callback=False) <ref-rpio-py>`


.. _ref-installation:

Installation
------------

The easiest way to install/update RPIO on a Raspberry Pi is with either ``easy_install`` or ``pip``::

    $ sudo apt-get install python-setuptools
    $ sudo easy_install -U RPIO

You can also get RPIO from Github repository, which is usually a step ahead of pypi::

    $ git clone https://github.com/metachris/RPIO.git
    $ cd RPIO
    $ sudo python setup.py install

Or from Github but without Git::

    $ curl -L https://github.com/metachris/RPIO/archive/master.tar.gz | tar -xz
    $ cd RPIO-master
    $ sudo python setup.py install

Debian packages are available at `metachris.github.com/rpio/download <http://metachris.github.com/rpio/download/>`_.

After the installation you can use ``import RPIO`` as well as the command-line tool ``rpio``.


Examples
--------

You can find lots of examples inside the `documentation <http://pythonhosted.org/RPIO>`_, as well as in the `/examples/ source directory <https://github.com/metachris/RPIO/tree/master/examples>`_.


Feedback
--------

Please send feedback and ideas to chris@linuxuser.at, and `open an issue at Github <https://github.com/metachris/RPIO/issues/new>`_ if
you've encountered a bug.


Links
-----

* https://github.com/metachris/RPIO
* http://pypi.python.org/pypi/RPIO
* http://pypi.python.org/pypi/RPi.GPIO
* http://www.raspberrypi.org/wp-content/uploads/2012/02/BCM2835-ARM-Peripherals.pdf
* https://www.kernel.org/doc/Documentation/gpio/gpio.txt
* `semver versioning standard <http://semver.org/>`_


License & Copyright
-------------------

::

    Copyright

        Copyright (C) 2013 Chris Hager <chris@linuxuser.at>

    License

        This program is free software: you can redistribute it and/or modify
        it under the terms of the GNU Lesser General Public License as published
        by the Free Software Foundation, either version 3 of the License, or
        (at your option) any later version.

        This program is distributed in the hope that it will be useful,
        but WITHOUT ANY WARRANTY; without even the implied warranty of
        MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
        GNU Lesser General Public License for more details at
        <http://www.gnu.org/licenses/lgpl-3.0-standalone.html>


Changes
-------

* v2.0.0-beta1

  * RPIO works with Raspberry Pi Zero, 2 and 3 (Thanks to Andy Baker and Reik Hua)

* v0.11.0

  * Merged various pull requests: Arch package link, bugfixes, allow Pi to control
    camera LED (GPIO 5 in BCM), Dont exit when soft_fatal in effect [`source <https://github.com/dbeal/RPIO/commit/fde45bc2842e56cd3341a596d029a8f8d58e9518>`_],

* v0.10.0

  * Auto-cleanup on exit (also shuts down ``wait_for_interrupts(threaded=True)``)
  * Bugfix in cpuinfo.c: correctly trim over-voltage header
  * rpio-curses: help shows raspberry sysinfo
  * switched argument ordering of wait_for_interrupts to (``wait_for_interrupts(threaded=False, epoll_timeout=1)``)
  * Added ``RPIO.Exceptions`` (list of C GPIO exceptions)

* v0.9.6

  * Added ``debounce_timeout_ms`` argument to ``RPIO.add_interrupt_callback(..)``
  * Added ``threaded`` argument to ``RPIO.wait_for_interrupts(..)``
  * Interrupt callbacks now receive integer values ``0`` or ``1`` instead of strings
  * Interrupt callbacks with edge=``rising`` or ``falling`` only receive the correct values
  * Added ``RPIO.close_tcp_client(fileno)``
  * Debian .deb package builds
  * License changed to GNU Lesser General Public License v3 or later (LGPLv3+)
  * Improved detection in cpuinfo.c

* v0.9.1

  * PWM
  * ``rpio-curses`` quits gracefully if terminal too small

* v0.8.5

  * Debug-options for ``rpio-curses``: You can now run it on any Linux/OSX machine with ``rpio-curses dev``

* v0.8.4

  * ``rpio-curses``
  * Bugfix in RPIO: tcp callbacks (first parameter ``socket`` works now)
  * Renamed ``RPIO.rpi_sysinfo()`` to ``RPIO.sysinfo``

* v0.8.3: pypi release update with updated documentation and bits of refactoring

* v0.8.2

  * Added TCP socket callbacks
  * ``RPIO`` does not auto-clean interfaces on exceptions anymore, but will auto-clean them
    as needed. This means you should now call ``RPIO.cleanup_interrupts()`` to properly close
    the sockets and unexport the interfaces.
  * Renamed ``RPIO.rpi_sysinfo()`` to ``RPIO.sysinfo()``


* v0.8.0

  * Improved auto-cleaning of interrupt interfaces
  * BOARD numbering scheme support for interrupts
  * Support for software pullup and -down resistor with interrupts
  * New method ``RPIO.set_pullupdn(..)``
  * ``rpio`` now supports P5 header gpios (28, 29, 30, 31) (only in BCM mode)
  * Tests added in ``source/run_tests.py`` and ``fabfile.py``
  * Major refactoring of C GPIO code
  * Various minor updates and fixes


* v0.7.1

  * Refactoring and cleanup of c_gpio
  * Added new constants and methods (see documentation above)
  * Bugfixes

    * ``wait_for_interrupts()`` now auto-cleans interfaces when an exception occurs. Before you needed to call ``RPIO.cleanup()`` manually.


* v0.6.4

  * Python 3 bugfix in `rpio`
  * Various minor updates
