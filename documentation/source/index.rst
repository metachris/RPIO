.. RPIO documentation master file, created by
   sphinx-quickstart on Thu Feb 21 13:13:51 2013.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to RPIO's documentation!
================================

RPIO is a GPIO toolbox for the Raspberry Pi.

* :ref:`RPIO.py <ref-rpio-py>`, an extension of `RPi.GPIO <http://pypi.python.org/pypi/RPi.GPIO>`_ with interrupt handling and :ref:`more <ref-rpio-py-rpigpio>`
* :ref:`rpio <ref-rpio-cmd>`, a command-line multitool for inspecting and manipulating GPIOs system-wide


Installation
============

The easiest way to install/update RPIO on a Raspberry Pi is with either ``easy_install`` or ``pip`` (you may need
to get it first with ``sudo apt-get install python-setuptools``)::

    $ sudo easy_install -U RPIO
    $ sudo pip install -U RPIO

Another way to get RPIO is directly from the Github repository::

    $ git clone https://github.com/metachris/RPIO.git
    $ cd RPIO
    $ sudo python setup.py install

After the installation you can use ``import RPIO`` as well as the command-line tool
``rpio``.

.. _ref-rpio-cmd:

`rpio`, the command line tool
=============================

``rpio`` allows you to inspect and manipulate GPIO's system wide, including those used by other processes.
``rpio`` needs to run with superuser privileges (root), else it will restart using ``sudo``. The BCM GPIO numbering
scheme is used by default.

::

    Show the help page:

        $ rpio -h

    Inspect the function and state of gpios (with -i/--inspect):

        $ rpio -i 7
        $ rpio -i 7,8,9
        $ rpio -i 1-9

        # Example output for `rpio -i 1-9` (non-existing are ommitted):
        GPIO 2: ALT0   (1)
        GPIO 3: ALT0   (1)
        GPIO 4: INPUT  (0)
        GPIO 7: OUTPUT (0)
        GPIO 8: INPUT  (1)
        GPIO 9: INPUT  (0)

    Inspect all GPIO's on this board (with -I/--inspect-all):

        $ rpio -I

    Set GPIO 7 to `1` (or `0`) (with -s/--set):

        $ rpio -s 7:1

        You can only write to pins that have been set up as OUTPUT. You can
        set this yourself with `--setoutput <gpio-id>`.

    Wait for interrupt events on GPIOs (with -w/--wait_for_interrupts). You
    can specify an edge (eg. `:rising`; default='both') as well as `:pullup`,
    `:pulldown` or `pulloff`.

        $ rpio -w 7
        $ rpio -w 7:rising
        $ rpio -w 7:falling:pullup

        $ rpio -w 7:rising:pullup,17,18
        $ rpio -w 1-9

    Setup a pin as INPUT (optionally with software resistor):

        $ rpio --setinput 7
        $ rpio --setinput 7:pullup
        $ rpio --setinput 7:pulldown

    Setup a pin as OUTPUT (optionally with an initial value (0 or 1)):

        $ rpio --setoutput 8
        $ rpio --setoutput 8:1

    Show Raspberry Pi system info:

        $ rpio --sysinfo

        # Example output:
        Model B, Revision 2.0, RAM: 256 MB, Maker: Sony


You can update the ``RPIO`` package to the latest version::

    $ rpio --update-rpio


Install (and update) the ``rpio`` manpage::

    $ rpio --update-man
    $ man rpio


.. _ref-rpio-py:

`RPIO.py`, the Python module
============================

RPIO.py extends `RPi.GPIO <http://pypi.python.org/pypi/RPi.GPIO>`_ with 
interrupt handling and :ref:`more <ref-rpio-py-goodies>`.

Interrupts are used to receive notifications from the kernel when GPIO state
changes occur. Advantages include minimized cpu consumption, very fast
notification times, and the ability to trigger on specific edge transitions
(``rising|falling|both``). RPIO uses the BCM GPIO numbering scheme by default. This
is an example of how to use RPIO to react on events on 3 pins by using
interrupts, each with different edge detections:

::

    # Setup logging
    import logging
    log_format = '%(levelname)s | %(asctime)-15s | %(message)s'
    logging.basicConfig(format=log_format, level=logging.DEBUG)

    # Get started
    import RPIO

    def do_something(gpio_id, value):
        logging.info("New value for GPIO %s: %s" % (gpio_id, value))

    RPIO.add_interrupt_callback(7, do_something)
    RPIO.add_interrupt_callback(8, do_something, edge='rising')
    RPIO.add_interrupt_callback(9, do_something, pull_up_down=RPIO.PUD_UP)
    RPIO.wait_for_interrupts()

Default edge is ``both`` and default pull_up_down is ``RPIO.PUD_OFF``. If 
you want to receive a callback inside a Thread (which won't block anything
else on the system), set ``threaded_callback=True`` when adding an interrupt-
callback. Here is an example:

::

    RPIO.add_interrupt_callback(7, do_something, threaded_callback=True)

Make sure to double-check the value returned from the interrupt, since it
is not necessarily corresponding to the edge (eg. 0 may come in as value,
even if `edge="rising"`). To remove all callbacks from a certain gpio pin, use
``RPIO.del_interrupt_callback(gpio_id)``. To stop the ``wait_for_interrupts()``
loop you can call ``RPIO.stop_waiting_for_interrupts()``.


.. _ref-rpio-py-rpigpio:

RPi.GPIO
--------

Besides the interrupt handling, you can use RPIO just as `RPi.GPIO <http://pypi.python.org/pypi/RPi.GPIO>`_:

::

    import RPIO

    # set up input channel without pull-up
    RPIO.setup(7, RPIO.IN)

    # set up input channel with pull-up control. Can be 
    # PUD_UP, PUD_DOWN or PUD_OFF (default)
    RPIO.setup(7, RPIO.IN, pull_up_down=RPIO.PUD_UP)

    # read input from gpio 7
    input_value = RPIO.input(7)

    # set up GPIO output channel
    RPIO.setup(8, RPIO.OUT)

    # set gpio 8 to high
    RPIO.output(8, True)

    # set up output channel with an initial state
    RPIO.setup(8, RPIO.OUT, initial=RPIO.LOW)

    # change to BOARD numbering schema
    RPIO.setmode(RPIO.BOARD)

    # set software pullup on channel 17
    RPIO.set_pullupdn(17, RPIO.PUD_UP)

    # reset every channel that has been set up by this program,
    # and unexport interrupt gpio interfaces
    RPIO.cleanup()

You can use RPIO as a drop-in replacement for RPi.GPIO in your existing code like this:

::

    import RPIO as GPIO  # (if you've previously used `import RPi.GPIO as GPIO`)


.. _ref-rpio-py-goodies:

Additions to RPi.GPIO
---------------------

Additional Constants

* ``RPIO.RPI_REVISION`` (either ``1`` or ``2``)
* ``RPIO.RPI_REVISION_HEX`` (``0002`` .. ``000f``)

Additional Methods

* ``RPIO.forceinput(gpio_id)`` - reads the value of any gpio without needing to call setup() first
* ``RPIO.forceoutput(gpio_id, value)`` - writes a value to any gpio without needing to call setup() first 
  (**warning**: this can potentially harm your Raspberry)
* ``RPIO.gpio_function(gpio_id)`` - returns the current setup of a gpio (``IN, OUT, ALT0``)
* ``RPIO.rpi_sysinfo()`` - returns ``(model, revision, mb-ram and maker)`` of this Raspberry
* ``RPIO.set_pullupdn(gpio_id, pud)`` - set a pullup or -down resistor on a GPIO

Interrupt Handling

* ``RPIO.add_interrupt_callback(gpio_id, callback, edge='both', threaded_callback=False)``
* ``RPIO.del_interrupt_callback(gpio_id)``
* ``RPIO.wait_for_interrupts(epoll_timeout=1)``
* ``RPIO.stop_waiting_for_interrupts()``
*  implemented with ``epoll``


Links
=====

* https://github.com/metachris/RPIO
* http://pypi.python.org/pypi/RPIO
* http://pypi.python.org/pypi/RPi.GPIO
* http://www.kernel.org/doc/Documentation/gpio.txt


Feedback
========

Please send any feedback to Chris Hager (chris@linuxuser.at) and `open an issue at Github <https://github.com/metachris/RPIO/issues>`_ if
you've encountered a bug.


License
=======

::

    RPIO is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    RPIO is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.


Updates
=======

* v0.7.2

  * BOARD numbering scheme supported with interrupts
  * Software pullup and -down resistor with interrupts
  * new method ``RPIO.set_pullupdn(..)``


* v0.7.1
  
  * Refactoring and cleanup of c_gpio
  * Added new constants and methods (see documentation above)
  * **Bugfixes**

    * ``wait_for_interrupts()`` now auto-cleans interfaces when an exception occurs. Before you needed to call ``RPIO.cleanup()`` manually.


* v0.6.4

  * Python 3 bugfix in `rpio`
  * Various minor updates
