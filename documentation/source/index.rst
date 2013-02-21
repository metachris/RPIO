.. RPIO documentation master file, created by
   sphinx-quickstart on Thu Feb 21 13:13:51 2013.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to RPIO's documentation!
================================

RPIO consists of two main parts:

* :ref:`rpio <ref-rpio-cmd>`, a command-line multitool for inspecting and manipulating GPIOs
* :ref:`RPIO.py <ref-rpio-py>`, a module which extends RPi.GPIO with interrupt handling and other good stuff


Installation
============

The easiest way to install RPIO on a Raspberry Pi is either with `pip`::

    $ sudo pip install RPIO

or `easy_install`::

    $ sudo easy_install RPIO

You can also clone the repository from Github and build it yourself:::

    $ git clone https://github.com/metachris/RPIO.git
    $ cd RPIO
    $ sudo python setup.py install

After the installation you can `import RPIO` as well as use the command-line tool
`rpio`.


.. _ref-rpio-cmd:

**rpio**, the command line tool
===============================

`rpio` is a command-line multitool which allows you to inspect and manipulate GPIO's 
system wide; including gpios used by other processes. rpio uses two new 
functions in py_gpio.c, namely `forceinput()` and
`forceoutput()`; to use those you'll need at least RPIO v0.1.8
(`sudo pip install --upgrade RPIO`). Note that rpio uses the BCM gpio
numbering scheme. Here are some examples of how to use `rpio`::

    Inspect the function and state of gpios (with -i/--inspect):

        $ rpio -i 17
        $ rpio -i 17,18,19
        $ rpio -i 4-10

        # Example output for `rpio -i 4-10`
        GPIO 4 : INPUT   [0]
        GPIO 5 : ALT0    [0]
        GPIO 6 : OUTPUT  [1]
        GPIO 7 : INPUT   [0]
        GPIO 8 : INPUT   [0]
        GPIO 9 : INPUT   [0]
        GPIO 10: INPUT   [1]

    Set GPIO 17 to either `0` or `1` (with -s/--set):

        $ rpio -s 17:1

        You can only write to pins that have been set up as OUTPUT. You can
        set this yourself with `--setoutput <gpio-id>`.

    Show interrupt events on GPIOs (with -w/--wait_for_interrupts;
    default edge='both'):

        $ rpio -w 17
        $ rpio -w 17:rising,18:falling,19
        $ rpio -w 17-24

    Setup a pin as INPUT (optionally with pullup or -down resistor):

        $ rpio --setinput 17
        $ rpio --setinput 17:pullup
        $ rpio --setinput 17:pulldown

    Setup a pin as OUTPUT:

        $ rpio --setoutput 18


.. _ref-rpio-py:

**RPIO**, the Python module
===========================

RPIO extends RPi.GPIO with interrupt handling. RPIO uses `GPIO.BCM` as default
GPIO numbering system, as opposed to the pin ids (`GPIO.BOARD`).

Interrupts are used to receive notifications from the kernel when GPIO state 
changes occur. Advantages include minimized cpu consumption, very fast
notification times, and the ability to trigger on specific edge transitions
(`'rising|falling|both'`). This is an example of how to use RPIO to react on 
events on 3 pins by using interrupts, each with different edge detections::

    import logging
    log_format = '%(levelname)s | %(asctime)-15s | %(message)s'
    logging.basicConfig(format=log_format, level=logging.DEBUG)
    import RPIO

    def do_something(gpio_id, value):
        logging.info("New value for GPIO %s: %s" % (gpio_id, value))

    RPIO.add_interrupt_callback(17, do_something, edge='rising')
    RPIO.add_interrupt_callback(18, do_something, edge='falling')
    RPIO.add_interrupt_callback(19, do_something, edge='both')
    RPIO.wait_for_interrupts()

If you want to receive a callback inside a Thread (which won't block anything
else on the system), set `threaded_callback` to True when adding an interrupt-
callback. Here is an example:::

    RPIO.add_interrupt_callback(17, do_something, edge='rising', threaded_callback=True)

Make sure to double-check the value returned from the interrupt, since it
is not necessarily corresponding to the edge (eg. 0 may come in as value,
even if edge="rising"). To remove all callbacks from a certain gpio pin, use
`RPIO.del_interrupt_callback(gpio_id)`. To stop the `wait_for_interrupts()`
loop you can call `RPIO.stop_waiting_for_interrupts()`.

Besides the interrupt handling, you can use RPIO just as RPi.GPIO:::

    import RPIO

    # set up GPIO output channel
    RPIO.setup(17, RPIO.OUT)

    # set gpio 17 to high
    RPIO.output(17, True)

    # set up output channel with an initial state
    RPIO.setup(18, RPIO.OUT, initial=RPIO.LOW)

    # set up input channel with pull-up control
    #   (pull_up_down be PUD_OFF, PUD_UP or PUD_DOWN, default PUD_OFF)
    RPIO.setup(19, RPIO.IN, pull_up_down=RPIO.PUD_UP)

    # read input from gpio 19
    input_value = RPIO.input(19)

    # change to BOARD GPIO numbering
    RPIO.setmode(RPIO.BOARD)

    # reset every channel that has been set up by this program. and unexport gpio interfaces
    RPIO.cleanup()


Feedback
========

Chris Hager (chris@linuxuser.at)


Links
=====

* https://github.com/metachris/RPIO
* http://pypi.python.org/pypi/RPi.GPIO
* http://www.kernel.org/doc/Documentation/gpio.txt
