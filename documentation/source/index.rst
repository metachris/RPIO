.. RPIO documentation master file, created by
   sphinx-quickstart on Thu Feb 21 13:13:51 2013.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to RPIO's documentation!
================================

RPIO is a Raspberry Pi GPIO toolbox, consisting of two main parts:

* :ref:`rpio <ref-rpio-cmd>`, a command-line multitool for inspecting and manipulating GPIOs
* :ref:`RPIO.py <ref-rpio-py>`, a module which extends RPi.GPIO with interrupt handling and other good stuff


Installation
============

The easiest way to install/update RPIO on a Raspberry Pi is with either easy_install or pip::

    $ sudo easy_install -U RPIO
    $ sudo pip install -U RPIO

Another way to get RPIO is directly from the Github repository::

    $ git clone https://github.com/metachris/RPIO.git
    $ cd RPIO
    $ sudo python setup.py install

After the installation you can use `import RPIO` as well as the command-line tool
`rpio`.

.. _ref-rpio-cmd:

`rpio`, the command line tool
=============================

`rpio` allows you to inspect and manipulate GPIO's system wide, including those used by other processes.
`rpio` needs to run with superuser privileges (root), else it will restart using `sudo`. The BCM GPIO numbering
scheme is used by default. Here are a few examples of using `rpio`:

::

    Show the help page:

        $ rpio -h

    Inspect the function and state of gpios (with -i/--inspect):

        $ rpio -i 7
        $ rpio -i 7,8,9
        $ rpio -i 1-9

        # Example output for `rpio -i 1-9` (non-existing are ommitted)
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

    Show interrupt events on GPIOs (with -w/--wait_for_interrupts;
    default edge='both'):

        $ rpio -w 7
        $ rpio -w 7:rising,8:falling,9
        $ rpio -w 1-9

    Setup a pin as INPUT (optionally with pullup or -down resistor):

        $ rpio --setinput 7
        $ rpio --setinput 7:pullup
        $ rpio --setinput 7:pulldown

    Setup a pin as OUTPUT:

        $ rpio --setoutput 8

    Show Raspberry Pi system info:

        $ rpio --sysinfo

        # Example output:
        Model B, Revision 2.0, RAM: 256 MB, Maker: Sony

You can update RPIO to the latest version with `--update-rpio`::

    $ rpio --update-rpio

`rpio` can install (and update) its manpage::

    $ rpio --update-man
    $ man rpio

`rpio` was introduced in version 0.5.1.

.. _ref-rpio-py:

`RPIO.py`, the Python module
============================

RPIO extends RPi.GPIO with interrupt handling and a few other goodies.

Interrupts are used to receive notifications from the kernel when GPIO state
changes occur. Advantages include minimized cpu consumption, very fast
notification times, and the ability to trigger on specific edge transitions
(`'rising|falling|both'`). RPIO uses the BCM GPIO numbering scheme by default. This
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

    RPIO.add_interrupt_callback(7, do_something, edge='rising')
    RPIO.add_interrupt_callback(8, do_something, edge='falling')
    RPIO.add_interrupt_callback(9, do_something, edge='both')
    RPIO.wait_for_interrupts()

If you want to receive a callback inside a Thread (which won't block anything
else on the system), set `threaded_callback` to True when adding an interrupt-
callback. Here is an example:

::

    RPIO.add_interrupt_callback(7, do_something, edge='rising', threaded_callback=True)

Make sure to double-check the value returned from the interrupt, since it
is not necessarily corresponding to the edge (eg. 0 may come in as value,
even if edge="rising"). To remove all callbacks from a certain gpio pin, use
`RPIO.del_interrupt_callback(gpio_id)`. To stop the `wait_for_interrupts()`
loop you can call `RPIO.stop_waiting_for_interrupts()`.

Besides the interrupt handling, you can use RPIO just as RPi.GPIO:

::

    import RPIO

    # set up input channel without pull-up
    RPIO.setup(7, RPIO.IN)

    # set up input channel with pull-up control
    #   (pull_up_down be PUD_OFF, PUD_UP or PUD_DOWN, default PUD_OFF)
    RPIO.setup(7, RPIO.IN, pull_up_down=RPIO.PUD_UP)

    # read input from gpio 7
    input_value = RPIO.input(7)

    # set up GPIO output channel
    RPIO.setup(8, RPIO.OUT)

    # set gpio 8 to high
    RPIO.output(8, True)

    # set up output channel with an initial state
    RPIO.setup(18, RPIO.OUT, initial=RPIO.LOW)

    # change to BOARD numbering schema (interrupts will still use BCM though)
    RPIO.setmode(RPIO.BOARD)

    # reset every channel that has been set up by this program. and unexport gpio interfaces
    RPIO.cleanup()

You can use RPIO as a drop-in replacement for RPi.GPIO in your existing code like this (if 
you've used the BCM gpio numbering scheme):

::

    import RPIO as GPIO  # (if you've previously used `import RPi.GPIO as GPIO`)


Feedback
========

Chris Hager (chris@linuxuser.at)

If you've encountered a bug, please let me know via Github: https://github.com/metachris/RPIO/issues.


Links
=====

* https://github.com/metachris/RPIO
* http://pypi.python.org/pypi/RPi.GPIO
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


Updates
=======

* v0.6.4: Python 3 bugfix in `rpio`
