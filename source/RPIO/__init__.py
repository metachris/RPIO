# -*- coding: utf-8 -*-
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
License: GPLv3
"""
import socket
import select
import os.path
import time

from logging import debug, info, warn, error
from threading import Thread
from functools import partial

import RPIO._GPIO as _GPIO

VERSION = "0.9.4"

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

# Internals
_SYS_GPIO_ROOT = '/sys/class/gpio/'
_TCP_SOCKET_HOST = "0.0.0.0"

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
    return (RPI_REVISION_HEX,) + \
            MODEL_DATA[RPI_REVISION_HEX.lstrip("0")]


def version():
    """ Returns a tuple of (VERSION, VERSION_GPIO) """
    return (VERSION, VERSION_GPIO)


class _RPIO:
    _epoll = select.epoll()
    _show_warnings = True

    # Interrupt callback maps
    _map_fileno_to_file = {}
    _map_fileno_to_gpioid = {}
    _map_fileno_to_options = {}
    _map_gpioid_to_fileno = {}
    _map_gpioid_to_callbacks = {}

    # Keep track of created kernel interfaces for later cleanup
    _gpio_kernel_interfaces_created = []

    # TCP socket stuff
    _tcp_client_sockets = {}  # { fileno: (socket, cb) }
    _tcp_server_sockets = {}  # { fileno: (socket, cb) }

    # Whether to continue the epoll loop or quit at next chance. You
    # can manually set this to False to stop `wait_for_interrupts()`.
    _is_waiting_for_interrupts = False

    def add_tcp_callback(self, port, callback, threaded_callback=False):
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
        self._epoll.register(serversocket.fileno(), select.EPOLLIN)

        # Prepare the callback (wrap in Thread if needed)
        cb = callback if not threaded_callback else \
                partial(_threaded_callback, callback)

        self._tcp_server_sockets[serversocket.fileno()] = (serversocket, cb)
        debug("Socket server started at port %s and callback added." % port)

    def add_interrupt_callback(self, gpio_id, callback, edge='both',
            pull_up_down=PUD_OFF, threaded_callback=False,
            debounce_timeout_ms=None):
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
            raise AttributeError("'%s' is not a valid pull_up_down." % edge)

        # Make sure the gpio_id is valid
        if not gpio_id in (GPIO_LIST_R1 if RPI_REVISION == 1 else \
                GPIO_LIST_R2):
            raise AttributeError("GPIO %s is not a valid gpio-id." % gpio_id)

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

        # If initial callback for this GPIO then set everything up. Else make
        # sure the edge detection is the same.
        if gpio_id in self._map_gpioid_to_callbacks:
            with open(path_gpio + "edge", "r") as f:
                e = f.read().strip()
                if e != edge:
                    raise AttributeError(("Cannot add callback for gpio %s:"
                            " edge detection '%s' not compatible with existing"
                            " edge detection '%s'.") % (gpio_id, edge, e))

            # Check whether edge is the same, else throw Exception
            debug("- kernel interface already setup for GPIO %s" % gpio_id)
            self._map_gpioid_to_callbacks[gpio_id].append(cb)

        else:
            # If kernel interface already exists unexport first for clean setup
            if os.path.exists(path_gpio):
                if self._show_warnings:
                    warn("Kernel interface for GPIO %s already exists." % \
                            gpio_id)
                debug("- unexporting kernel interface for GPIO %s" % gpio_id)
                with open(_SYS_GPIO_ROOT + "unexport", "w") as f:
                    f.write("%s" % gpio_id)
                time.sleep(0.1)

            # Export kernel interface /sys/class/gpio/gpioN
            with open(_SYS_GPIO_ROOT + "export", "w") as f:
                f.write("%s" % gpio_id)
            self._gpio_kernel_interfaces_created.append(gpio_id)
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
            self._map_fileno_to_file[f.fileno()] = f
            self._map_fileno_to_gpioid[f.fileno()] = gpio_id
            self._map_fileno_to_options[f.fileno()] = {
                    "debounce_timeout_s": debounce_timeout_ms / 1000.0 if \
                            debounce_timeout_ms else 0,
                    "interrupt_last": 0,
                    "edge": edge
                    }
            self._map_gpioid_to_fileno[gpio_id] = f.fileno()
            self._map_gpioid_to_callbacks[gpio_id] = [cb]

            # Add to epoll
            self._epoll.register(f.fileno(), select.EPOLLPRI | select.EPOLLERR)

    def del_interrupt_callback(self, gpio_id):
        """ Delete all interrupt callbacks from a certain gpio """
        debug("- removing interrupts on gpio %s" % gpio_id)
        gpio_id = channel_to_gpio(gpio_id)
        fileno = self._map_gpioid_to_fileno[gpio_id]

        # 1. Remove from epoll
        self._epoll.unregister(fileno)

        # 2. Cache the file
        f = self._map_fileno_to_file[fileno]

        # 3. Remove from maps
        del self._map_fileno_to_file[fileno]
        del self._map_fileno_to_gpioid[fileno]
        del self._map_fileno_to_options[fileno]
        del self._map_gpioid_to_fileno[gpio_id]
        del self._map_gpioid_to_callbacks[gpio_id]

        # 4. Close file last in case of IOError
        f.close()

    def _handle_interrupt(self, fileno, val):
        """ Internally distributes interrupts to all attached callbacks """
        val = int(val)

        # Filter invalid edge values (sometimes 1 comes in when edge=falling)
        edge = self._map_fileno_to_options[fileno]["edge"]
        if (edge == 'rising' and val == 0) or (edge == 'falling' and val == 1):
            return

        # If user activated debounce for this callback, check timing now
        debounce = self._map_fileno_to_options[fileno]["debounce_timeout_s"]
        if debounce:
            t = time.time()
            t_last = self._map_fileno_to_options[fileno]["interrupt_last"]
            if t - t_last < debounce:
                debug("- don't start interrupt callback due to debouncing")
                return
            self._map_fileno_to_options[fileno]["interrupt_last"] = t

        # Start the callback(s) now
        gpio_id = self._map_fileno_to_gpioid[fileno]
        if gpio_id in self._map_gpioid_to_callbacks:
            for cb in self._map_gpioid_to_callbacks[gpio_id]:
                cb(gpio_id, val)

    def close_tcp_client(self, fileno):
        debug("closing client socket fd %s" % fileno)
        self._epoll.unregister(fileno)
        socket, cb = self._tcp_client_sockets[fileno]
        socket.close()
        del self._tcp_client_sockets[fileno]

    def wait_for_interrupts(self, epoll_timeout=1):
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
        self._is_waiting_for_interrupts = True
        #try:
        while self._is_waiting_for_interrupts:
            events = self._epoll.poll(epoll_timeout)
            for fileno, event in events:
                debug("- epoll event on fd %s: %s" % (fileno, event))
                if fileno in self._tcp_server_sockets:
                    # New client connection to socket server
                    serversocket, cb = self._tcp_server_sockets[fileno]
                    connection, address = serversocket.accept()
                    connection.setblocking(0)
                    f = connection.fileno()
                    self._epoll.register(f, select.EPOLLIN)
                    self._tcp_client_sockets[f] = (connection, cb)

                elif event & select.EPOLLIN:
                    # Input from TCP socket
                    socket, cb = self._tcp_client_sockets[fileno]
                    content = socket.recv(1024)
                    if not content or not content.strip():
                        # No content means quitting
                        self.close_tcp_client(fileno)
                    else:
                        sock, cb = self._tcp_client_sockets[fileno]
                        cb(self._tcp_client_sockets[fileno][0], \
                                content.strip())

                elif event & select.EPOLLHUP:
                    # TCP Socket Hangup
                    self.close_tcp_client(fileno)

                elif event & select.EPOLLPRI:
                    # GPIO interrupts
                    f = self._map_fileno_to_file[fileno]
                    # read() is workaround for not getting new values
                    # with read(1)
                    val = f.read().strip()
                    f.seek(0)
                    self._handle_interrupt(fileno, val)

        #except:
        #    debug("RPIO: auto-cleaning interfaces after an exception")
        #    cleanup_interfaces()
        #    cleanup_tcpsockets()
        #    raise

    def stop_waiting_for_interrupts(self):
        """
        Ends the blocking `wait_for_interrupts()` loop the next time it can,
        which depends on the `epoll_timeout` (per default its 1 second).
        """
        self._is_waiting_for_interrupts = False

    def cleanup_interfaces(self):
        """
        Removes all /sys/class/gpio/gpioN interfaces that this script created,
        and deletes callback bindings. Should be used after using interrupts.
        """
        debug("Cleaning up interfaces...")
        for gpio_id in self._gpio_kernel_interfaces_created:
            # Close the value-file and remove interrupt bindings
            self.del_interrupt_callback(gpio_id)

            # Remove the kernel GPIO interface
            debug("- unexporting GPIO %s" % gpio_id)
            with open(_SYS_GPIO_ROOT + "unexport", "w") as f:
                f.write("%s" % gpio_id)

        # Reset list of created interfaces
        self._gpio_kernel_interfaces_created = []

    def cleanup_tcpsockets(self):
        """
        Closes all TCP connections and then the socket servers
        """
        for fileno in self._tcp_client_sockets.keys():
            self.close_tcp_client(fileno)
        for fileno, items in self._tcp_server_sockets.items():
            socket, cb = items
            debug("- _cleanup server socket connection (fd %s)" % fileno)
            self._epoll.unregister(fileno)
            socket.close()
        self._tcp_server_sockets = {}

    def cleanup_interrupts(self):
        """
        Clean up all interrupt-related sockets and interfaces. Recommended to
        use before exiting your program! After this you'll need to re-add the
        interrupt callbacks before waiting for interrupts again.
        """
        self.cleanup_tcpsockets()
        self.cleanup_interfaces()


# To be able to use RPIO as RPi.GPIO, create RPIO class and expose methods here
_rpio = _RPIO()


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


def close_tcp_client(self, fileno):
    """ Closes TCP connection to a client and removes client from epoll """
    _rpio.close_tcp_client(fileno)


def wait_for_interrupts(epoll_timeout=1, threaded=False):
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
    started in a Thread. To quit it, call `RPIO.stop_waiting_for_interrupts()`.
    """
    if threaded:
        Thread(target=_rpio.wait_for_interrupts, args=(epoll_timeout,)).start()
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
    Clean up all interrupt-related sockets and interfaces. Recommended to
    use before exiting your program! After this you'll need to re-add the
    interrupt callbacks before waiting for interrupts again.
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
