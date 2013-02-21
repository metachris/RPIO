"""
RPIO extends RPi.GPIO with interrupt handling. Importing this also sets
the default mode to GPIO.BCM (the same numbering system the kernel uses,
as opposed to the pin ids (GPIO.BOARD)).

You can use RPIO the same way as RPi.GPIO (eg. RPIO.setmode(...),
RPIO.input(...)), as well as access the new interrupt handling methods.
The following example shows how to react on events on 3 pins by using
interrupts, each with different edge detections:

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

    RPIO.add_interrupt_callback(17, do_something, edge='rising',
            threaded_callback=True)

Make sure to double-check the value returned from the interrupt, since it
is not necessarily corresponding to the edge (eg. 0 may come in as value,
even if edge="rising").

To remove all callbacks from a certain gpio pin, use
`RPIO.del_interrupt_callback(gpio_id)`. To stop the `wait_for_interrupts()`
loop you can call `RPIO.stop_waiting_for_interrupts()`.

Author: Chris Hager <chris@linuxuser.at>
License: GPLv3
URL: https://github.com/metachris/RPIO
"""
import select
import os.path

from logging import debug, info, warn, error
from threading import Thread
from functools import partial

from GPIO import *
from GPIO import cleanup as _cleanup_orig

VERSION = "0.5.2"

# BCM numbering mode by default
setmode(BCM)

# Interrupt callback maps
_map_fileno_to_file = {}
_map_fileno_to_gpioid = {}
_map_gpioid_to_fileno = {}
_map_gpioid_to_callbacks = {}

# Keep track of created kernel interfaces for later cleanup
_gpio_kernel_interfaces_created = []

# Whether to continue the epoll loop or quit at next chance. You
# can manually set this to False to stop `wait_for_interrupts()`.
_is_waiting_for_interrupts = False

# Internals
_epoll = select.epoll()
_SYS_GPIO_ROOT = '/sys/class/gpio/'
_RPI_SYSINFO = None
GPIO_FUNCTIONS = {0: "OUTPUT", 1: "INPUT", 4: "ALT0", 7: "-"}
MODEL_DATA = {
    '0002': ('B', '1.0', 256, '?'),
    '0003': ('B', '1.0', 256, '?'),
    '0004': ('B', '2.0', 256, 'Sony'),
    '0005': ('B', '2.0', 256, 'Qisda'),
    '0006': ('B', '2.0', 256, 'Egoman'),
    '0007': ('A', '2.0', 256, 'Egoman'),
    '0008': ('A', '2.0', 256, 'Sony'),
    '0009': ('A', '2.0', 256, 'Qisda'),
    '000d': ('B', '2.0', 512, 'Egoman'),
    '000e': ('B', '2.0', 512, 'Sony'),
    '000f': ('B', '2.0', 512, 'Qisda')
}

# Pin layout with GPIO numbers (pin-id range is 1 - 26)
_DC5V = -1
_DC3V3 = -2
_GND = -3
PIN_TO_GPIO_LAYOUT_REV1 = (_DC3V3, _DC5V, 0, 5, 1, _GND, 4, 14, _GND, 15, \
        17, 18, 21, _GND, 22, 23, _DC3V3, 24, 10, _GND, 9, 25, 11, 8, _GND, 7)
PIN_TO_GPIO_LAYOUT_REV2 = (_DC3V3, _DC5V, 2, _DC5V, 3, _GND, 4, 14, _GND, 15, \
        17, 18, 27, _GND, 22, 23, _DC3V3, 24, 10, _GND, 9, 25, 11, 8, _GND, 7)


def get_rpi_sysinfo():
    """ Returns (model, revision, mb-ram and maker) for this raspberry """
    global _RPI_SYSINFO
    if _RPI_SYSINFO:
        return _RPI_SYSINFO

    import re
    with open("/proc/cpuinfo") as f:
        cpuinfo = f.read()
    rev_hex = re.search(r"(?<=\nRevision)[ |:|\t]*\w+", cpuinfo) \
            .group().strip(" :\t")
    _RPI_SYSINFO = MODEL_DATA[rev_hex]
    return _RPI_SYSINFO


def is_valid_gpio_id(gpio_id, board_rev=None):
    """
    Returns True/False depending on whether the supplied gpio_id is valid on
    the current board. board_rev is either '1.0' or '2.0'
    """
    if not board_rev:
        board_rev = get_rpi_sysinfo()[1]
    return int(gpio_id) in (PIN_TO_GPIO_LAYOUT_REV2 \
            if board_rev == "2.0" else PIN_TO_GPIO_LAYOUT_REV1)


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
    debug("Adding callback for GPIO %s" % gpio_id)
    if not edge in ["falling", "rising", "both", "none"]:
        raise AttributeError("'%s' is not a valid edge." % edge)

    # Make sure the gpio_id is valid
    if not is_valid_gpio_id(gpio_id):
        raise AttributeError("GPIO %s is not a valid gpio-id for this board." \
                % gpio_id)

    # Require INPUT pin setup
    if gpio_function(int(gpio_id)) != 1:
        raise IOError(("GPIO %s cannot be used for interrupts because it's "
                "setup as %s instead of INPUT.") % (gpio_id, \
                GPIO_FUNCTIONS[gpio_function(int(gpio_id))]))

    # Prepare the callback (wrap in Thread if needed)
    cb = callback if not threaded_callback else \
            partial(_threaded_callback, callback)

    # Check if /sys/class/gpio/gpioN interface exists; else create it
    path_gpio = "%sgpio%s/" % (_SYS_GPIO_ROOT, gpio_id)
    if not os.path.exists(path_gpio):
        with open(_SYS_GPIO_ROOT + "export", "w") as f:
            f.write("%s" % gpio_id)
        _gpio_kernel_interfaces_created.append(gpio_id)
        debug("- kernel interface created for GPIO %s" % gpio_id)

    # If initial callback for this GPIO then set everything up. Else make sure
    # the edge detection is the same and add this to the callback list.
    if gpio_id in _map_gpioid_to_callbacks:
        with open(path_gpio + "edge", "r") as f:
            e = f.read().strip()
            if e != edge:
                raise AttributeError(("Cannot add callback for gpio %s:"
                        " edge detection '%s' not compatible with existing"
                        " edge detection '%s'.") % (gpio_id, edge, e))

        # Check whether edge is the same, else throw Exception
        debug("- kernel interface already configured for GPIO %s" % gpio_id)
        _map_gpioid_to_callbacks[gpio_id].append(cb)

    else:
        # Configure gpio as input
        with open(path_gpio + "direction", "w") as f:
            f.write("in")

        # Configure gpio edge detection
        with open(path_gpio + "edge", "w") as f:
            f.write(edge)

        debug("- kernel interface configured for GPIO %s (edge='%s')" % \
                (gpio_id, edge))

        # Open the gpio value stream and read the initial value
        f = open(path_gpio + "value", 'r')
        val_initial = f.read().strip()
        debug("- inital gpio value: %s" % val_initial)
        f.seek(0)

        # Add callback info to the mapping dictionaries
        _map_fileno_to_file[f.fileno()] = f
        _map_fileno_to_gpioid[f.fileno()] = gpio_id
        _map_gpioid_to_fileno[gpio_id] = f.fileno()
        _map_gpioid_to_callbacks[gpio_id] = [cb]

        # Add to epoll
        _epoll.register(f.fileno(), select.EPOLLPRI | select.EPOLLERR)


def del_interrupt_callback(gpio_id):
    """ Delete all interrupt callbacks from a certain gpio """
    fileno = _map_gpioid_to_fileno[gpio_id]

    # 1. Remove from epoll
    _epoll.unregister(fileno)

    # 2. Close the open file
    f = _map_fileno_to_file[fileno]
    f.close()

    # 3. Remove from maps
    del _map_fileno_to_file[fileno]
    del _map_fileno_to_gpioid[fileno]
    del _map_gpioid_to_fileno[gpio_id]
    del _map_gpioid_to_callbacks[gpio_id]


def _handle_interrupt(fileno, val):
    """ Internally distributes interrupts to all attached callbacks """
    gpio_id = _map_fileno_to_gpioid[fileno]
    if gpio_id in _map_gpioid_to_callbacks:
        for cb in _map_gpioid_to_callbacks[gpio_id]:
            # Start the callback!
            cb(gpio_id, val)


def wait_for_interrupts(epoll_timeout=1):
    """
    Blocking loop to listen for GPIO interrupts and distribute them to
    associated callbacks. epoll_timeout is an easy way to shutdown the
    blocking function. Per default the timeout is set to 1 second; if
    `_is_waiting_for_interrupts` is set to False the loop will exit.
    """
    global _is_waiting_for_interrupts
    _is_waiting_for_interrupts = True
    while _is_waiting_for_interrupts:
        events = _epoll.poll(epoll_timeout)
        for fileno, event in events:
            if event & select.EPOLLPRI:
                f = _map_fileno_to_file[fileno]
                # read() is workaround for not getting new values with read(1)
                val = f.read().strip()
                f.seek(0)
                _handle_interrupt(fileno, val)


def stop_waiting_for_interrupts():
    """
    Ends the blocking `wait_for_interrupts()` loop the next time it can,
    which depends on the `epoll_timeout` (per default its 1 second).
    """
    global _is_waiting_for_interrupts
    _is_waiting_for_interrupts = False


def _cleanup_interfaces():
    """
    Remove all /sys/class/gpio/gpioN interfaces that this script created.
    Does not usually need to be used.
    """
    global _gpio_kernel_interfaces_created
    for gpio_id in _gpio_kernel_interfaces_created:
        # Remove the kernel GPIO interface
        with open(_SYS_GPIO_ROOT + "unexport", "w") as f:
            f.write("%s" % gpio_id)

    _gpio_kernel_interfaces_created = []


def cleanup():
    """
    Clean up by resetting all GPIO channels that have been used by this
    program to INPUT with no pullup/pulldown and no event detection. Also
    unexports the interfaces that have been set up for interrupts.
    """
    _cleanup_interfaces()
    _cleanup_orig()
