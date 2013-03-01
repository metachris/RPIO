"""
RPIO extends RPi.GPIO with GPIO interrupts, TCP socket interrupts and more.

You can use RPIO the same way as RPi.GPIO (eg. RPIO.setmode(...),
RPIO.input(...)), as well as access the new interrupt handling methods. The
following example shows how to react on events on 3 pins, and one socket
server on port 8080. The interrupts can have optional `edge` and
`pull_up_down` parameters (default edge is `both` and default pull_up_down is
`RPIO.PUD_OFF`.):

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

Now you can connect to the socket server with `$ telnet localhost 8080` and
send input to your callback.

If you want to receive a callback inside a Thread (which won't block anything
else on the system), set `threaded_callback` to True when adding an interrupt-
callback. Here is an example:

    RPIO.add_interrupt_callback(7, do_something, threaded_callback=True)
    RPIO.add_tcp_callback(8080, socket_callback, threaded_callback=True))


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
import socket
import select
import os.path

from logging import debug, info, warn, error
from threading import Thread
from functools import partial
from time import sleep

from GPIO import *
from GPIO import cleanup as _cleanup_orig
from GPIO import setmode as _setmode

VERSION = "0.8.3"

# BCM numbering mode by default
setmode(BCM)

# Interrupt callback maps
_map_fileno_to_file = {}
_map_fileno_to_gpioid = {}
_map_gpioid_to_fileno = {}
_map_gpioid_to_callbacks = {}

# Keep track of created kernel interfaces for later cleanup
_gpio_kernel_interfaces_created = []

# TCP socket stuff
_TCP_SOCKET_HOST = "0.0.0.0"
_tcp_client_sockets = {}  # { fileno: (socket, cb) }
_tcp_server_sockets = {}  # { fileno: (socket, cb) }

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


def _threaded_callback(callback, *args):
    """ Internal wrapper to start a callback in threaded mode """
    Thread(target=callback, args=args).start()


def sysinfo():
    """ Returns (model, revision, mb-ram and maker) for this raspberry """
    return (RPI_REVISION_HEX,) + MODEL_DATA[RPI_REVISION_HEX.lstrip("0")]


def add_tcp_callback(port, callback, threaded_callback=False):
    """
    Adds a unix socket server callback, which will be invoked when values
    arrive from a connected socket client. The callback must accept two
    parameters, eg. ``def callback(socket, msg)``.
    """
    if not callback:
        raise AttributeError("No callback")

    serversocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    serversocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    serversocket.bind((_TCP_SOCKET_HOST, port))
    serversocket.listen(1)
    serversocket.setblocking(0)
    _epoll.register(serversocket.fileno(), select.EPOLLIN)

    # Prepare the callback (wrap in Thread if needed)
    cb = callback if not threaded_callback else \
            partial(_threaded_callback, callback)

    _tcp_server_sockets[serversocket.fileno()] = (serversocket, cb)
    debug("Socket server started at port %s and callback added." % port)


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
        # If kernel interface already exists, unexport first for clean setup
        if os.path.exists(path_gpio):
            debug("- unexporting kernel interface for GPIO %s" % gpio_id)
            with open(_SYS_GPIO_ROOT + "unexport", "w") as f:
                f.write("%s" % gpio_id)
            sleep(0.1)

        # Export kernel interface /sys/class/gpio/gpioN
        with open(_SYS_GPIO_ROOT + "export", "w") as f:
            f.write("%s" % gpio_id)
        global _gpio_kernel_interfaces_created
        _gpio_kernel_interfaces_created.append(gpio_id)
        debug("- kernel interface exported for GPIO %s" % gpio_id)

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


def _close_tcp_client(fileno):
    debug("closing client socket fd %s" % fileno)
    global _tcp_client_sockets
    _epoll.unregister(fileno)
    socket, cb = _tcp_client_sockets[fileno]
    socket.close()
    del _tcp_client_sockets[fileno]


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
    #try:
    while _is_waiting_for_interrupts:
        events = _epoll.poll(epoll_timeout)
        for fileno, event in events:
            if fileno in _tcp_server_sockets:
                # New client connection to socket server
                serversocket, cb = _tcp_server_sockets[fileno]
                connection, address = serversocket.accept()
                connection.setblocking(0)
                f = connection.fileno()
                _epoll.register(f, select.EPOLLIN)
                _tcp_client_sockets[f] = (connection, cb)

            elif event & select.EPOLLIN:
                # Input from TCP socket
                socket, cb = _tcp_client_sockets[fileno]
                content = socket.recv(1024)
                if not content or not content.strip():
                    # No content means quitting
                    _close_tcp_client(fileno)
                else:
                    sock, cb = _tcp_client_sockets[fileno]
                    cb(_tcp_client_sockets[fileno][0], content.strip())

            elif event & select.EPOLLHUP:
                # TCP Socket Hangup
                _close_tcp_client(fileno)

            elif event & select.EPOLLPRI:
                # GPIO interrupts
                f = _map_fileno_to_file[fileno]
                # read() is workaround for not getting new values
                # with read(1)
                val = f.read().strip()
                f.seek(0)
                _handle_interrupt(fileno, val)

    #except:
    #    debug("RPIO: auto-cleaning interfaces after an exception")
    #    _cleanup_interfaces()
    #    _cleanup_tcpsockets()
    #    raise


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


def _cleanup_tcpsockets():
    """
    Closes all TCP connections and then the socket servers
    """
    global _tcp_server_sockets
    for fileno in _tcp_client_sockets.keys():
        _close_tcp_client(fileno)
    for fileno, items in _tcp_server_sockets.items():
        socket, cb = items
        debug("- _cleanup server socket connection (fd %s)" % fileno)
        _epoll.unregister(fileno)
        socket.close()
    _tcp_server_sockets = {}


def cleanup_interrupts():
    """
    Clean up all interrupt-related sockets and interfaces. Recommended to
    use before exiting your program! After this you'll need to re-add the
    interrupt callbacks before waiting for interrupts again.
    """
    _cleanup_tcpsockets()
    _cleanup_interfaces()


def cleanup():
    """
    Clean up by resetting all GPIO channels that have been used by this
    program to INPUT with no pullup/pulldown and no event detection. Also
    unexports the interrupt interfaces and callback bindings. You'll need
    to add the interrupt callbacks again before waiting for interrupts again.
    """
    cleanup_interrupts()
    _cleanup_orig()


def version():
    """ Returns a tuple of (VERSION, VERSION_GPIO) """
    return (VERSION, VERSION_GPIO)
