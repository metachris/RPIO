Welcome to RPIO's documentation!
================================

RPIO is an advanced GPIO module for the Raspberry Pi.

* GPIO input and output (drop-in replacement for `RPi.GPIO <http://pypi.python.org/pypi/RPi.GPIO>`_)
* GPIO interrupts (callbacks when events occur on input gpios)
* TCP socket interrupts (callbacks when tcp socket clients send data)
* PWM via DMA (up to 1µs resolution; 500kHz)
* Command-line tools ``rpio`` and ``rpio-curses``
* Well documented, fast source code with minimal CPU usage
* Open source (GPLv3+)

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

After the installation you can use ``import RPIO`` as well as the command-line tool ``rpio``.


Examples
--------

You can find lots of examples inside the `documentation <http://pythonhosted.org/RPIO>`_, as well as in the `/examples/ source directory <https://github.com/metachris/RPIO/tree/master/examples>`_.


Feedback
--------

Please send feedback and ideas to chris@linuxuser.at, and `open an issue at Github <https://github.com/metachris/RPIO/issues/new>`_ if
you've encountered a bug.


FAQ
---

**How does RPIO work?**

  RPIO extends RPi.GPIO, a GPIO controller written in C which uses a low-level memory interface. Interrupts are
  implemented  with ``epoll`` via ``/sys/class/gpio/``. For more detailled information take a look at the `source <https://github.com/metachris/RPIO/tree/master/source>`_, it's well documented and easy to build.


**Should I update RPIO often?**

  Yes, because RPIO is getting better by the day. You can use ``$ rpio --update-rpio`` or see :ref:`Installation <ref-installation>` for more information about methods to update.


**I've encountered a bug, what next?**

  * Make sure you are using the latest version of RPIO (see :ref:`Installation <ref-installation>`)
  * Open an issue at Github

    * Go to https://github.com/metachris/RPIO/issues/new
    * Describe the problem and steps to replicate
    * Add the output of ``$ rpio --version`` and ``$ rpio --sysinfo``


**pip is throwing an error during the build:** ``source/c_gpio/py_gpio.c:9:20: fatal error: Python.h: No such file or directory``

  You need to install the ``python-dev`` package (eg. ``$ sudo apt-get install python-dev``), or use ``easy_install`` (see :ref:`Installation <ref-installation>`).


Links
-----

* https://github.com/metachris/RPIO
* http://pypi.python.org/pypi/RPIO
* http://pypi.python.org/pypi/RPi.GPIO
* http://www.raspberrypi.org/wp-content/uploads/2012/02/BCM2835-ARM-Peripherals.pdf
* http://www.kernel.org/doc/Documentation/gpio.txt


License
-------

::

    RPIO is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    RPIO is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.


Changes
-------

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
