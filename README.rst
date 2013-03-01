Visit `pythonhosted.org/RPIO <http://pythonhosted.org/RPIO>`_ for a pretty version of this documentation.

RPIO is an advanced GPIO module for the Raspberry Pi.

* GPIO Input and Output (drop-in replacement for `RPi.GPIO <http://pypi.python.org/pypi/RPi.GPIO>`_)
* GPIO Interrupts (callbacks when events occur on input gpios)
* TCP Socket Interrupts (callbacks when tcp socket clients send data)
* Well documented, tested, fast source code
* Minimal CPU and memory profile

RPIO consists of two main components:

* RPIO.py, which you can import in Python 2 or 3 with ``import RPIO``
* rpio, a command-line multitool for inspecting and manipulating GPIOs system-wide


New in v0.8.2

* Socket server callbacks with RPIO.add_tcp_callback(port, callback, threaded_callback=False)




Installation
============

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




``rpio``, the command line tool
===============================

``rpio`` includes two command-line tools which allow you to inspect and manipulate GPIO's system wide, 
including those used by other processes:

* ``rpio`` - command line program
* ``rpio-curses`` - rpio with a graphical user interface for the terminal

``rpio-curses``
---------------
``rpio-curses`` is a curses-based graphical user interface for the terminal. It updates
the gpio infos (function and state) every second by default. Here are a few screenshots:

* http://imgur.com/rOl9VvG
* http://imgur.com/iB1LkW6
* http://imgur.com/lhRvjIl


``rpio``
--------
``rpio`` needs to run with superuser privileges (root), else it will restart using ``sudo``. The BCM GPIO numbering
scheme is used by default. ``rpio --inspect-all`` (or ``-I``) is the most popular command; it shows you all gpios
on the board, with function and state. Here is an overview of all the functions:

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

    Set GPIO 7 output to `1` (or `0`) (with -s/--set):

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
        000e: Model B, Revision 2.0, RAM: 256 MB, Maker: Sony


You can update the ``RPIO`` package to the latest version::

    $ rpio --update-rpio


Install (and update) the ``rpio`` manpage::

    $ rpio --update-man
    $ man rpio




``RPIO.py``, the Python module
==============================

RPIO.py extends `RPi.GPIO <http://pypi.python.org/pypi/RPi.GPIO>`_ in
various ways, and uses the BCM GPIO numbering scheme by default.

* GPIO Interrupts 
* TCP Socket Interrupts 
* GPIO Input & Output 
* more




GPIO Interrupts
---------------
Interrupts are used to receive notifications from the kernel when GPIO state
changes occur. Advantages include minimized cpu consumption, very fast
notification times, and the ability to trigger on specific edge transitions
(``rising``, ``falling`` or ``both``). You can also set a software pull-up 
or pull-down resistor.

RPIO.add_interrupt_callback(gpio_id, callback, edge='both', pull_up_down=RPIO.PUD_OFF, threaded_callback=False)

   Adds a callback to receive notifications when a GPIO changes it's value. Possible ``pull_up_down`` values are 
   ``RPIO.PUD_UP``, ``RPIO.PUD_DOWN`` and ``RPIO.PUD_OFF`` (default). Possible edges are ``rising``,
   ``falling`` and ``both`` (default). Note that ``rising`` and ``falling`` edges may receive values
   not corresponding to the edge, so be sure to double check.




TCP Socket Interrupts
---------------------
Its easy to open ports for incoming TCP connections with just this one method:

RPIO.add_tcp_callback(port, callback, threaded_callback=False)

   Adds a socket server callback, which will be started when a connected socket client sends something. This is implemented
   by RPIO creating a TCP server socket at the specified port. Incoming connections will be accepted when ``RPIO.wait_for_interrupts()`` runs.
   The callback must accept exactly two parameters: socket and message (eg. ``def callback(socket, msg)``). The callback can use the socket parameter to send values back to the client (eg. ``socket.send("hi there\n")``).

   You can test the TCP socket interrupts with ``$ telnet <your-ip> <your-port>`` (eg. ``$ telnet localhost 8080``). An empty string
   tells the server to close the client connection (for instance if you just press enter in telnet, you'll get disconnected).



Example
-------

The following example shows how to react to events on three gpios, and one socket 
server on port 8080::

    import RPIO

    def gpio_callback(gpio_id, val):
        print("gpio %s: %s" % (gpio_id, val))

    def socket_callback(socket, val):
        print("socket %s: '%s'" % (socket.fileno(), val))
        socket.send("echo: %s\n" % val)

    # Three GPIO interrupt callbacks
    RPIO.add_interrupt_callback(7, gpio_callback)
    RPIO.add_interrupt_callback(8, gpio_callback, edge='rising')
    RPIO.add_interrupt_callback(9, gpio_callback, pull_up_down=RPIO.PUD_UP)

    # One TCP socket server callback on port 8080
    RPIO.add_tcp_callback(8080, socket_callback)

    # Start the blocking epoll loop, and catch Ctrl+C KeyboardInterrupt
    try:
        RPIO.wait_for_interrupts()
    except KeyboardInterrupt:
        RPIO.cleanup_interrupts()


If you want to receive a callback inside a Thread (to not block RPIO from returning to wait
for interrupts), set ``threaded_callback`` to ``True`` when adding it::


    # for GPIO interrupts
    RPIO.add_interrupt_callback(7, do_something, threaded_callback=True)

    # for socket interrupts
    RPIO.add_tcp_callback(8080, socket_callback, threaded_callback=True)

To stop the ``wait_for_interrupts()`` loop you can call ``RPIO.stop_waiting_for_interrupts()``.
After using ``RPIO.wait_for_interrupts()`` you should call ``RPIO.cleanup_interrupts()`` before your 
program quits, to shut everything down nicely.


Log Output
----------

To enable RPIO log output, import ``logging`` and set the loglevel to ``DEBUG`` before importing RPIO::

    import logging
    log_format = '%(levelname)s | %(asctime)-15s | %(message)s'
    logging.basicConfig(format=log_format, level=logging.DEBUG)
    import RPIO




GPIO Input & Output
-------------------

RPIO extends `RPi.GPIO <http://pypi.python.org/pypi/RPi.GPIO>`_;
all the input and output handling works just the same:

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
    RPIO.set_pullupdn(17, RPIO.PUD_UP)  # new in RPIO

    # get the function of channel 8
    RPIO.gpio_function(8)

    # reset every channel that has been set up by this program,
    # and unexport interrupt gpio interfaces
    RPIO.cleanup()

You can use RPIO as a drop-in replacement for RPi.GPIO in your existing code like this:

::

    import RPIO as GPIO  # (if you've previously used `import RPi.GPIO as GPIO`)

To find out more about the methods and constants in RPIO you can run ``$ sudo pydoc RPIO``, or
use the help method inside Python::

    import RPIO
    help(RPIO)




Additions to RPi.GPIO
---------------------

Additional Constants

* ``RPIO.RPI_REVISION`` - the current board's revision (either ``1`` or ``2``)
* ``RPIO.RPI_REVISION_HEX`` - the cpu hex revision code (``0002`` .. ``000f``)

Additional Methods

* ``RPIO.gpio_function(gpio_id)`` - returns the current setup of a gpio (``IN, OUT, ALT0``)
* ``RPIO.set_pullupdn(gpio_id, pud)`` - set a pullup or -down resistor on a GPIO
* ``RPIO.forceinput(gpio_id)`` - reads the value of any gpio without needing to call setup() first
* ``RPIO.forceoutput(gpio_id, value)`` - writes a value to any gpio without needing to call setup() first 
  (**warning**: this can potentially harm your Raspberry)
* ``RPIO.sysinfo()`` - returns ``(hex_rev, model, revision, mb-ram and maker)`` of this Raspberry
* ``RPIO.version()`` - returns ``(version_rpio, version_cgpio)``

Interrupt Handling

* ``RPIO.add_interrupt_callback(gpio_id, callback, edge='both', pull_up_down=RPIO.PUD_OFF, threaded_callback=False)``
* ``RPIO.add_tcp_callback(port, callback, threaded_callback=False)``
* ``RPIO.del_interrupt_callback(gpio_id)``
* ``RPIO.wait_for_interrupts(epoll_timeout=1)``
* ``RPIO.stop_waiting_for_interrupts()``
*  implemented with ``epoll``


Feedback
========

Please send feedback and ideas to chris@linuxuser.at, and `open an issue at Github <https://github.com/metachris/RPIO/issues/new>`_ if
you've encountered a bug.


FAQ
===

**How does RPIO work?**

  RPIO extends RPi.GPIO, a GPIO controller written in C which uses a low-level memory interface. Interrupts are
  implemented  with ``epoll`` via ``/sys/class/gpio/``. For more detailled information take a look at the `source <https://github.com/metachris/RPIO/tree/master/source>`_, it's well documented and easy to build.


**Should I update RPIO often?**

  Yes, because RPIO is getting better by the day. You can use ``$ rpio --update-rpio`` or see Installation for more information about methods to update.


**I've encountered a bug, what next?**

  * Make sure you are using the latest version of RPIO (see Installation)
  * Open an issue at Github

    * Go to https://github.com/metachris/RPIO/issues/new
    * Describe the problem and steps to replicate
    * Add the output of ``$ rpio --version`` and ``$ rpio --sysinfo``


**pip is throwing an error during the build:** ``source/c_gpio/py_gpio.c:9:20: fatal error: Python.h: No such file or directory``

  You need to install the ``python-dev`` package (eg. ``$ sudo apt-get install python-dev``), or use ``easy_install`` (see Installation).


Links
=====

* https://github.com/metachris/RPIO
* http://pypi.python.org/pypi/RPIO
* http://pypi.python.org/pypi/RPi.GPIO
* http://www.raspberrypi.org/wp-content/uploads/2012/02/BCM2835-ARM-Peripherals.pdf
* http://www.kernel.org/doc/Documentation/gpio.txt


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


Changes
=======

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
