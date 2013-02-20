RPIO extends RPi.GPIO with easy interrupt handling, and provides a command
line tool `rpio` which allows you to inspect and manipulate gpio's even if
they are owned by another process.

The easiest way to get RPIO is with pip or easy_install:

::

    sudo pip install RPIO

Interrupts are used to receive notifications from the kernel when GPIO state 
changes occur. Advantages include minimized cpu consumption, very fast
notification times, and the ability to trigger on specific edge transitions
(`'rising|falling|both'`). This is an example of how to use RPIO:

::

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
callback. Here is an example:

::

    RPIO.add_interrupt_callback(17, do_something, edge='rising', threaded_callback=True)

Make sure to double-check the value returned from the interrupt, since it
is not necessarily corresponding to the edge (eg. 0 may come in as value,
even if edge="rising"). To remove all callbacks from a certain gpio pin, use
`RPIO.del_interrupt_callback(gpio_id)`. To stop the `wait_for_interrupts()`
loop you can call `RPIO.stop_waiting_for_interrupts()`.

If an interrupt occurs while your callback function does something blocking
(like `time.sleep()` outside a thread), events will not arrive until you
release the block. Only one process can receive interrupts for a specific GPIO
pin, since the read on `/sys/class/gpio/gpio<N>/value` destroys the value for
subsequent reads. RPIO uses `epoll` to receive interrupts from the kernel.


RPi.GPIO
========

You can use all of RPi.GPIO's functionality through RPIO. Note that RPIO uses GPIO.BCM pin numbering by default

::

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


Links
=====
* https://github.com/metachris/raspberrypi-utils
* http://pypi.python.org/pypi/RPi.GPIO
* http://www.kernel.org/doc/Documentation/gpio.txt


Feedback 
========
Chris Hager (<chris@linuxuser.at>)


Todo
====
- [ ] `GPIO.input(...)` can set a pullup/pulldown resistor, which is not yet part
of this interrupt extension (since there is no option for it in /sys/class/gpio/...).
Note to self: A possible solution is to replicate the function from `RPi.GPIO.input()`.


License
=======
RPIO is free software, released under the MIT license.

::

    Copyright (c) 2013 Chris Hager <chris@linuxuser.at>

    Permission is hereby granted, free of charge, to any person obtaining a copy of
    this software and associated documentation files (the "Software"), to deal in
    the Software without restriction, including without limitation the rights to
    use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies
    of the Software, and to permit persons to whom the Software is furnished to do
    so, subject to the following conditions:

    The above copyright notice and this permission notice shall be included in all
    copies or substantial portions of the Software.

    THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
    IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
    FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
    AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
    LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
    OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
    SOFTWARE.