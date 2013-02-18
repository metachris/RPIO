"""
GPIO2 extends RPi.GPIO with interrupt handling. Importing this also sets
the default mode to GPIO.BCM (the same numbering system the kernel uses,
as opposed to the pin ids (GPIO.BOARD)).

You can use GPIO2 the same way as RPi.GPIO (eg. GPIO2.setmode(...),
GPIO2.input(...)), as well as access the new interrupt handling methods.
The following example shows how to react on events on 3 pins by using
interrupts, each with different edge detections:

    import GPIO2

    def do_something(gpio_id, value):
        print "New value for GPIO %s: %s" % (gpio_id, value)

    GPIO2.add_interrupt_callback(17, do_something, edge='rising')
    GPIO2.add_interrupt_callback(18, do_something, edge='falling')
    GPIO2.add_interrupt_callback(19, do_something, edge='both')
    GPIO2.wait_for_interrupts()

If you want to receive a callback inside a Thread (which won't block anything
else on the system), set `threaded_callback` to True when adding an interrupt-
callback. Here is an example:

    GPIO2.add_interrupt_callback(17, do_something, edge='rising',
            threaded_callback=True)

To remove all callbacks from a certain gpio pin, use
`GPIO2.del_interrupt_callback(gpio_id)`. To stop the `wait_for_interrupts()`
loop you can either set `GPIO2.is_waiting_for_interrupts` to `False`, or call
`GPOP2.stop_waiting_for_interrupts()`.

Author: Chris Hager <chris@linuxuser.at>
License: MIT
URL: https://github.com/metachris/raspberrypi-utils
"""
import select
import os.path
from threading import Thread
from functools import partial

from RPi.GPIO import *

# BCM numbering mode by default
setmode(BCM)

SYS_GPIO_ROOT = '/sys/class/gpio/'
epoll = select.epoll()

# Interrupt callback maps
map_fileno_to_file = {}
map_fileno_to_gpioid = {}
map_gpioid_to_fileno = {}
map_gpioid_to_callbacks = {}

# Keep track of created kernel interfaces for later cleanup
gpio_kernel_interfaces_created = []

# Whether to continue the epoll loop or quit at next chance. You
# can manually set this to False to stop `wait_for_interrupts()`.
is_waiting_for_interrupts = False


def _threaded_callback(callback, *args):
    """ Internal wrapper to start a callback in threaded mode """
    Thread(target=callback, args=args).start()


def add_interrupt_callback(gpio_id, callback, edge='both',
        threaded_callback=False):
    """
    Add a callback to be executed when the value on 'gpio_id' changes to the
    edge specified via the 'edge' parameter (default='both').

    If threaded_callback is True, the callback will be started inside a Thread.
    """
    # Prepare the callback (wrap in Thread if needed)
    cb = callback if not threaded_callback else \
            partial(_threaded_callback, callback)

    # Check if /sys/class/gpio/gpioN interface exists; else create it
    path_gpio = "%sgpio%s/" % (SYS_GPIO_ROOT, gpio_id)
    if not os.path.exists(path_gpio):
        with open(SYS_GPIO_ROOT + "export", "w") as f:
            f.write("%s" % gpio_id)
        gpio_kernel_interfaces_created.append(gpio_id)
        print "Kernel interface created for GPIO %s" % gpio_id

    # If initial callback for this GPIO then set everything up. Else make sure
    # the edge detection is the same and add this to the callback list.
    if gpio_id in map_gpioid_to_callbacks:
        with open(path_gpio + "edge", "r") as f:
            e = f.read().strip()
            if e != edge:
                raise AttributeError(("Cannot add callback for gpio %s:"
                        " edge detection '%s' not compatible with existing"
                        " edge detection '%s'.") % (gpio_id, edge, e))

        # Check whether edge is the same, else throw Exception
        print "Kernel interface already configured for GPIO %s" % gpio_id
        map_gpioid_to_callbacks[gpio_id].append(cb)

    else:
        # Configure gpio as input
        with open(path_gpio + "direction", "w") as f:
            f.write("in")

        # Configure gpio edge detection
        with open(path_gpio + "edge", "w") as f:
            f.write(edge)

        print "Kernel interface configured for GPIO %s" % gpio_id

        # Open the gpio value stream
        f = open(path_gpio + "value", 'r')
        val = f.read().strip()
        print "- inital gpio value: %s" % val

        # Add callback info to the mapping dictionaries
        map_fileno_to_file[f.fileno()] = f
        map_fileno_to_gpioid[f.fileno()] = gpio_id
        map_gpioid_to_fileno[gpio_id] = f.fileno()
        map_gpioid_to_callbacks[gpio_id] = [cb]

        # Add to epoll
        epoll.register(f.fileno(), select.EPOLLPRI | select.EPOLLET)


def del_interrupt_callback(gpio_id):
    """ Delete all interrupt callbacks from a certain gpio """
    fileno = map_gpioid_to_fileno[gpio_id]

    # 1. Remove from epoll
    epoll.unregister(fileno)

    # 2. Close the open file
    f = map_fileno_to_file[fileno]
    f.close()

    # 3. Remove from maps
    del map_fileno_to_file[fileno]
    del map_fileno_to_gpioid[fileno]
    del map_gpioid_to_fileno[gpio_id]
    del map_gpioid_to_callbacks[gpio_id]


def _handle_interrupt(fileno, val):
    """ Internally distributes interrupts to all attached callbacks """
    gpio_id = map_fileno_to_gpioid[fileno]
    if gpio_id in map_gpioid_to_callbacks:
        for cb in map_gpioid_to_callbacks[gpio_id]:
            # Start the callback!
            cb(gpio_id, val)


def wait_for_interrupts(epoll_timeout=1):
    """
    Blocking loop to listen for GPIO interrupts and distribute them to
    associated callbacks. epoll_timeout is an easy way to shutdown the
    blocking function. Per default the timeout is set to 1 second; if
    `is_waiting_for_interrupts` is set to False the loop will exit.
    """
    global is_waiting_for_interrupts
    is_waiting_for_interrupts = True
    while is_waiting_for_interrupts:
        events = epoll.poll(epoll_timeout)
        for fileno, event in events:
            if event & select.EPOLLPRI:
                f = map_fileno_to_file[fileno]
                f.seek(0)
                # read() is workaround for not getting new values with read(1)
                val = f.read().strip()
                _handle_interrupt(fileno, val)


def stop_waiting_for_interrupts():
    """
    Ends the blocking `wait_for_interrupts()` loop the next time it can,
    which depends on the `epoll_timeout` (per default its 1 second).
    """
    global is_waiting_for_interrupts
    is_waiting_for_interrupts = False


def cleanup_interfaces():
    """
    Remove all /sys/class/gpio/gpioN interfaces that this script created.
    Does not usually need to be used.
    """
    global gpio_kernel_interfaces_created
    for gpio_id in gpio_kernel_interfaces_created:
        # Remove the kernel GPIO interface
        with open(SYS_GPIO_ROOT + "unexport", "w") as f:
            f.write("%s" % gpio_id)

    gpio_kernel_interfaces_created = []
