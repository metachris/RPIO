"""
RPIO extends RPi.GPIO with interrupt handling. Importing this also sets
the default mode to GPIO.BCM (the same numbering system the kernel uses,
as opposed to the pin ids (GPIO.BOARD)).

You can use RPIO the same way as RPi.GPIO (eg. RPIO.setmode(...),
RPIO.input(...)), as well as access the new interrupt handling methods.
The following example shows how to react on events on 3 pins by using
interrupts, each with different edge detections:

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

Default edge is `both` and default pull_up_down is `RPIO.PUD_OFF`.

If you want to receive a callback inside a Thread (which won't block anything
else on the system), set `threaded_callback` to True when adding an interrupt-
callback. Here is an example:

    RPIO.add_interrupt_callback(7, do_something, threaded_callback=True)

Make sure to double-check the value returned from the interrupt, since it
is not necessarily corresponding to the edge (eg. 0 may come in as value,
even if edge="rising"). To remove all callbacks from a certain gpio pin, use
`RPIO.del_interrupt_callback(gpio_id)`. To stop the `wait_for_interrupts()`
loop you can call `RPIO.stop_waiting_for_interrupts()`.

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
License: GPLv3
"""
import select
import os.path

from logging import debug, info, warn, error
from threading import Thread
from functools import partial

from GPIO import *
from GPIO import cleanup as _cleanup_orig
from GPIO import setmode as _setmode

VERSION = "0.7.2"

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
GPIO_FUNCTIONS = {0: "OUTPUT", 1: "INPUT", 4: "ALT0", 7: "-"}
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
_PULL_UPDN = ("PUD_OFF", "PUD_DOWN", "PUD_UP")

# List of valid bcm gpio ids for raspberry rev1 and rev2
GPIO_LIST_R1 = (0, 1, 4, 7, 8, 9, 10, 11, 14, 15, 17, 18, 21, 22, 23, 24, 25)
GPIO_LIST_R2 = (2, 3, 4, 7, 8, 9, 10, 11, 14, 15, 17, 18, 22, 23, 24, 25, \
        27, 28, 29, 30, 31)


def _threaded_callback(callback, *args):
    """ Internal wrapper to start a callback in threaded mode """
    Thread(target=callback, args=args).start()


def rpi_sysinfo():
    """ Returns (model, revision, mb-ram and maker) for this raspberry """
    return MODEL_DATA[RPI_REVISION_HEX.lstrip("0")]


def add_interrupt_callback(gpio_id, callback, edge='both',
        pull_up_down=PUD_OFF, threaded_callback=False):
    """
    Add a callback to be executed when the value on 'gpio_id' changes to
    the edge specified via the 'edge' parameter (default='both').

    `pull_up_down` can be set to `RPIO.PUD_UP`, `RPIO.PUD_DOWN`, and
    `RPIO.PUD_OFF`.

    If `threaded_callback` is True, the callback will be started
    inside a Thread.
    """
    gpio_id = channel_to_gpio(gpio_id)
    debug("Adding callback for GPIO %s" % gpio_id)
    if not edge in ["falling", "rising", "both", "none"]:
        raise AttributeError("'%s' is not a valid edge." % edge)

    if not pull_up_down in [PUD_UP, PUD_DOWN, PUD_OFF]:
        raise AttributeError("'%s' is not a valid pull_up_down value." % edge)

    # Make sure the gpio_id is valid
    if not gpio_id in (GPIO_LIST_R1 if RPI_REVISION == 1 else GPIO_LIST_R2):
        raise AttributeError("GPIO %s is not a valid gpio-id for this board." \
                % gpio_id)

    # Require INPUT pin setup; and set the correct PULL_UPDN
    if gpio_function(int(gpio_id)) == IN:
        set_pullupdn(gpio_id, pull_up_down)
    else:
        debug("- changing gpio function from %s to INPUT" % \
                (GPIO_FUNCTIONS[gpio_function(int(gpio_id))]))
        setup(gpio_id, IN, pull_up_down)

    # Prepare the callback (wrap in Thread if needed)
    cb = callback if not threaded_callback else \
            partial(_threaded_callback, callback)

    # Prepare the /sys/class path of this gpio
    path_gpio = "%sgpio%s/" % (_SYS_GPIO_ROOT, gpio_id)

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
        # Export kernel interface /sys/class/gpio/gpioN
        # If it already exists, unexport first to be sure to clean up
        if os.path.exists(path_gpio):
            with open(_SYS_GPIO_ROOT + "unexport", "w") as f:
                f.write("%s" % gpio_id)

        # Always export it on first usage
        with open(_SYS_GPIO_ROOT + "export", "w") as f:
            f.write("%s" % gpio_id)
        global _gpio_kernel_interfaces_created
        _gpio_kernel_interfaces_created.append(gpio_id)
        debug("- kernel interface created for GPIO %s" % gpio_id)

        # Configure gpio as input
        with open(path_gpio + "direction", "w") as f:
            f.write("in")

        # Configure gpio edge detection
        with open(path_gpio + "edge", "w") as f:
            f.write(edge)

        debug(("- kernel interface configured for GPIO %s "
                "(edge='%s', pullupdn=%s)") % (gpio_id, edge, \
                _PULL_UPDN[pull_up_down]))

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
    debug("- removing interrupts on gpio %s" % gpio_id)
    gpio_id = channel_to_gpio(gpio_id)
    fileno = _map_gpioid_to_fileno[gpio_id]

    # 1. Remove from epoll
    _epoll.unregister(fileno)

    # 2. Cache the file
    f = _map_fileno_to_file[fileno]

    # 3. Remove from maps
    del _map_fileno_to_file[fileno]
    del _map_fileno_to_gpioid[fileno]
    del _map_gpioid_to_fileno[gpio_id]
    del _map_gpioid_to_callbacks[gpio_id]

    # 4. Close file last. In case of IOError everything else has been shutdown
    f.close()


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

    If an exception occurs while waiting for interrupts, the interrupt
    gpio interfaces will be cleaned up (/sys/class/gpio unexports). In
    this case all interrupts will be reset and you'd need to add the
    callbacks again before using `wait_for_interrupts(..)` again.
    """
    global _is_waiting_for_interrupts
    _is_waiting_for_interrupts = True
    try:
        while _is_waiting_for_interrupts:
            events = _epoll.poll(epoll_timeout)
            for fileno, event in events:
                if event & select.EPOLLPRI:
                    f = _map_fileno_to_file[fileno]
                    # read() is workaround for not getting new values
                    # with read(1)
                    val = f.read().strip()
                    f.seek(0)
                    _handle_interrupt(fileno, val)
    except:
        debug("RPIO auto-cleaning interfaces at exception")
        _cleanup_interfaces()
        raise


def stop_waiting_for_interrupts():
    """
    Ends the blocking `wait_for_interrupts()` loop the next time it can,
    which depends on the `epoll_timeout` (per default its 1 second).
    """
    global _is_waiting_for_interrupts
    _is_waiting_for_interrupts = False


def _cleanup_interfaces():
    """
    Remove all /sys/class/gpio/gpioN interfaces that this script created,
    and delete all callback bindings. Should be used after using interrupts.
    """
    debug("Cleaning up interfaces...")
    global _gpio_kernel_interfaces_created
    for gpio_id in _gpio_kernel_interfaces_created:
        # Close the value-file and remove interrupt bindings
        try:
            del_interrupt_callback(gpio_id)
        except:
            pass

        # Remove the kernel GPIO interface
        debug("- unexporting GPIO %s" % gpio_id)
        with open(_SYS_GPIO_ROOT + "unexport", "w") as f:
            f.write("%s" % gpio_id)

    # Reset list of created interfaces
    _gpio_kernel_interfaces_created = []


def cleanup():
    """
    Clean up by resetting all GPIO channels that have been used by this
    program to INPUT with no pullup/pulldown and no event detection. Also
    unexports the interrupt interfaces and callback bindings. You'll need
    to add the interrupt callbacks again before waiting for interrupts again.
    """
    _cleanup_interfaces()
    _cleanup_orig()
