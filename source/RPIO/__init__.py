# -*- coding: utf-8 -*-
#
# This file is part of RPIO.
#
# Copyright
#
#     Copyright (C) 2013 Chris Hager <chris@linuxuser.at>
#
# License
#
#     This program is free software: you can redistribute it and/or modify
#     it under the terms of the GNU Lesser General Public License as published
#     by the Free Software Foundation, either version 3 of the License, or
#     (at your option) any later version.
#
#     This program is distributed in the hope that it will be useful,
#     but WITHOUT ANY WARRANTY; without even the implied warranty of
#     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#     GNU Lesser General Public License for more details at
#     <http://www.gnu.org/licenses/lgpl-3.0-standalone.html>
#
# Documentation
#
#     http://pythonhosted.org/RPIO
#
"""
RPIO extends RPi.GPIO with GPIO interrupts, TCP socket interrupts and more.

Example of how to listen for interrupts with RPIO:

    import RPIO

    def gpio_callback(gpio_id, val):
        print("gpio %s: %s" % (gpio_id, val))

    def socket_callback(socket, val):
        print("socket %s: '%s'" % (socket.fileno(), val))
        socket.send("echo: %s" % val)

    # Three GPIO interrupt callbacks
    RPIO.add_interrupt_callback(7, gpio_callback)
    RPIO.add_interrupt_callback(9, gpio_callback, pull_up_down=RPIO.PUD_UP)

    # One TCP socket server callback on port 8080
    RPIO.add_tcp_callback(8080, socket_callback)

    # Start the blocking epoll loop (exit with Ctrl+C)
    RPIO.wait_for_interrupts()

You can add the argument `threaded=True` to `wait_for_interrupts(..)` in order
to run it in a thread. RPIO will automatically shutdown everything nicely when
your script exits.

GPIO interrupts can have optional `edge` and `pull_up_down` parameters (default
edge is `both` and default pull_up_down is `RPIO.PUD_OFF`).

If you want to receive a callback inside a Thread (which won't block anything
else on the system), set `threaded_callback` to True when adding an interrupt-
callback. Here is an example:

    RPIO.add_interrupt_callback(7, do_something, threaded_callback=True)
    RPIO.add_tcp_callback(8080, socket_callback, threaded_callback=True))

To debounce GPIO interrupts, you can add the argument ``debounce_timeout_ms``
to the ``add_interrupt_callback(..)`` call:

    RPIO.add_interrupt_callback(7, do_something, debounce_timeout_ms=100)

To stop the `wait_for_interrupts()` loop, call
`RPIO.stop_waiting_for_interrupts()`. To remove all callbacks from a certain
gpio pin, use `RPIO.del_interrupt_callback(gpio_id)`.

Besides the interrupt handling, you can use RPIO just as RPi.GPIO:

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

You can use RPIO as a drop-in replacement for RPi.GPIO in your existing code:

    import RPIO as GPIO  # (if you've used `import RPi.GPIO as GPIO`)

Author: Chris Hager <chris@linuxuser.at>
URL: https://github.com/metachris/RPIO
License: LGPLv3+
"""
from threading import Thread
import RPIO._GPIO as _GPIO
from RPIO._RPIO import Interruptor


VERSION = "0.10.0"

# Exposing constants from RPi.GPIO
VERSION_GPIO = _GPIO.VERSION_GPIO
RPI_REVISION = _GPIO.RPI_REVISION
RPI_REVISION_HEX = _GPIO.RPI_REVISION_HEX
HIGH = _GPIO.HIGH
LOW = _GPIO.LOW
OUT = _GPIO.OUT
IN = _GPIO.IN
ALT0 = _GPIO.ALT0
BOARD = _GPIO.BOARD
BCM = _GPIO.BCM
PUD_OFF = _GPIO.PUD_OFF
PUD_UP = _GPIO.PUD_UP
PUD_DOWN = _GPIO.PUD_DOWN

# Exposing methods from RPi.GPIO
setup = _GPIO.setup
output = _GPIO.output
input = _GPIO.input
setmode = _GPIO.setmode
forceoutput = _GPIO.forceoutput
forceinput = _GPIO.forceinput
set_pullupdn = _GPIO.set_pullupdn
gpio_function = _GPIO.gpio_function
channel_to_gpio = _GPIO.channel_to_gpio

# BCM numbering mode by default
_GPIO.setmode(BCM)

MODEL_DATA = {
    '2': ('B', '1.0', 256, '?'),
    '3': ('B', '1.0', 256, '?'),
    '4': ('B', '2.0', 256, 'Sony'),
    '5': ('B', '2.0', 256, 'Qisda'),
    '6': ('B', '2.0', 256, 'Egoman'),
    '7': ('A', '2.0', 256, 'Egoman'),
    '8': ('A', '2.0', 256, 'Sony'),
    '9': ('A', '2.0', 256, 'Qisda'),
    'd': ('B', '2.0', 512, 'Egoman'),
    'e': ('B', '2.0', 512, 'Sony'),
    'f': ('B', '2.0', 512, 'Qisda')
}

# List of valid bcm gpio ids for raspberry rev1 and rev2. Used for inspect-all.
GPIO_LIST_R1 = (0, 1, 4, 7, 8, 9, 10, 11, 14, 15, 17, 18, 21, 22, 23, 24, 25)
GPIO_LIST_R2 = (2, 3, 4, 7, 8, 9, 10, 11, 14, 15, 17, 18, 22, 23, 24, 25, \
        27, 28, 29, 30, 31)

# List of board pins with extra information which board header they belong to.
# Revision 2 boards have extra gpios on the P5 header (gpio 27-31)). Shifting
# the header info left by 8 bits leaves 255 possible channels per header. This
# list of board pins is currently only used for testing purposes.
HEADER_P5 = 5 << 8
PIN_LIST = (3, 5, 7, 8, 10, 11, 12, 13, 15, 16, 18, 19, 21, 22, 23, 24, 26, \
        3 | HEADER_P5, 4 | HEADER_P5, 5 | HEADER_P5, 6 | HEADER_P5)

# _rpio is the interrupt handling wrapper object
_rpio = Interruptor()


def sysinfo():
    """ Returns (model, revision, mb-ram, maker) for this raspberry """
    return (RPI_REVISION_HEX,) + MODEL_DATA[RPI_REVISION_HEX.lstrip("0")]


def version():
    """ Returns a tuple of (VERSION, VERSION_GPIO) """
    return (VERSION, VERSION_GPIO)


def add_tcp_callback(port, callback, threaded_callback=False):
    """
    Adds a unix socket server callback, which will be invoked when values
    arrive from a connected socket client. The callback must accept two
    parameters, eg. ``def callback(socket, msg)``.
    """
    _rpio.add_tcp_callback(port, callback, threaded_callback)


def add_interrupt_callback(gpio_id, callback, edge='both', \
        pull_up_down=PUD_OFF, threaded_callback=False, \
        debounce_timeout_ms=None):
    """
    Add a callback to be executed when the value on 'gpio_id' changes to
    the edge specified via the 'edge' parameter (default='both').

    `pull_up_down` can be set to `RPIO.PUD_UP`, `RPIO.PUD_DOWN`, and
    `RPIO.PUD_OFF`.

    If `threaded_callback` is True, the callback will be started
    inside a Thread.

    If debounce_timeout_ms is set, new interrupts will not be forwarded
    until after the specified amount of milliseconds.
    """
    _rpio.add_interrupt_callback(gpio_id, callback, edge, pull_up_down, \
            threaded_callback, debounce_timeout_ms)


def del_interrupt_callback(gpio_id):
    """ Delete all interrupt callbacks from a certain gpio """
    _rpio.del_interrupt_callback(gpio_id)


def close_tcp_client(fileno):
    """ Closes TCP connection to a client and removes client from epoll """
    _rpio.close_tcp_client(fileno)


def wait_for_interrupts(threaded=False, epoll_timeout=1):
    """
    Blocking loop to listen for GPIO interrupts and distribute them to
    associated callbacks. epoll_timeout is an easy way to shutdown the
    blocking function. Per default the timeout is set to 1 second; if
    `_is_waiting_for_interrupts` is set to False the loop will exit.

    If an exception occurs while waiting for interrupts, the interrupt
    gpio interfaces will be cleaned up (/sys/class/gpio unexports). In
    this case all interrupts will be reset and you'd need to add the
    callbacks again before using `wait_for_interrupts(..)` again.

    If the argument `threaded` is True, wait_for_interrupts will be
    started in a daemon Thread. To quit it, call
    `RPIO.stop_waiting_for_interrupts()`.
    """
    if threaded:
        t = Thread(target=_rpio.wait_for_interrupts, args=(epoll_timeout,))
        t.daemon = True
        t.start()
    else:
        _rpio.wait_for_interrupts(epoll_timeout)


def stop_waiting_for_interrupts():
    """
    Ends the blocking `wait_for_interrupts()` loop the next time it can,
    which depends on the `epoll_timeout` (per default its 1 second).
    """
    _rpio.stop_waiting_for_interrupts()


def cleanup_interrupts():
    """
    Removes all callbacks and closes used GPIO interfaces and sockets. After
    this you'll need to re-add the interrupt callbacks before waiting for
    interrupts again. Since RPIO v0.10.0 this is done automatically on exit.
    """
    _rpio.cleanup_interrupts()


def cleanup():
    """
    Clean up by resetting all GPIO channels that have been used by this
    program to INPUT with no pullup/pulldown and no event detection. Also
    unexports the interrupt interfaces and callback bindings. You'll need
    to add the interrupt callbacks again before waiting for interrupts again.
    """
    cleanup_interrupts()
    _GPIO.cleanup()


def setwarnings(enabled=True):
    """ Show warnings (either `True` or `False`) """
    _GPIO.setwarnings(enabled)
    _rpio._show_warnings = enabled
