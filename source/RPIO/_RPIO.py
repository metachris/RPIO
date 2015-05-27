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
import socket
import select
import os.path
import time
import atexit

from logging import debug, info, warn, error
from threading import Thread
from functools import partial
from itertools import chain

import RPIO
import RPIO._GPIO as _GPIO

# Internals
_SYS_GPIO_ROOT = '/sys/class/gpio/'
_TCP_SOCKET_HOST = "0.0.0.0"
GPIO_FUNCTIONS = {0: "OUTPUT", 1: "INPUT", 4: "ALT0", 6:"ALT2", 7: "-"}

_PULL_UPDN = ("PUD_OFF", "PUD_DOWN", "PUD_UP")


def _threaded_callback(callback, *args):
    """
    Internal wrapper to start a callback in threaded mode. Using the
    daemon mode to not block the main thread from exiting.
    """
    t = Thread(target=callback, args=args)
    t.daemon = True
    t.start()


def exit_handler():
    """ Auto-cleanup on exit """
    RPIO.stop_waiting_for_interrupts()
    RPIO.cleanup_interrupts()

atexit.register(exit_handler)


class Interruptor:
    """
    Object-based wrapper for interrupt management.
    """
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
            pull_up_down=_GPIO.PUD_OFF, threaded_callback=False,
            debounce_timeout_ms=None):
        """
        Add a callback to be executed when the value on 'gpio_id' changes to
        the edge specified via the 'edge' parameter (default='both').

        `pull_up_down` can be set to `RPIO.PUD_UP`, `RPIO.PUD_DOWN`, and
        `RPIO.PUD_OFF`.

        If `threaded_callback` is True, the callback will be started
        inside a Thread.
        """
        gpio_id = _GPIO.channel_to_gpio(gpio_id)
        debug("Adding callback for GPIO %s" % gpio_id)
        if not edge in ["falling", "rising", "both", "none"]:
            raise AttributeError("'%s' is not a valid edge." % edge)

        if not pull_up_down in [_GPIO.PUD_UP, _GPIO.PUD_DOWN, _GPIO.PUD_OFF]:
            raise AttributeError("'%s' is not a valid pull_up_down." % edge)

        # Make sure the gpio_id is valid
        if not gpio_id in set(chain(RPIO.GPIO_LIST_R1, RPIO.GPIO_LIST_R2, \
                              RPIO.GPIO_LIST_R3)):
            raise AttributeError("GPIO %s is not a valid gpio-id." % gpio_id)

        # Require INPUT pin setup; and set the correct PULL_UPDN
        if RPIO.gpio_function(int(gpio_id)) == RPIO.IN:
            RPIO.set_pullupdn(gpio_id, pull_up_down)
        else:
            debug("- changing gpio function from %s to INPUT" % \
                    (GPIO_FUNCTIONS[RPIO.gpio_function(int(gpio_id))]))
            RPIO.setup(gpio_id, RPIO.IN, pull_up_down)

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
        gpio_id = _GPIO.channel_to_gpio(gpio_id)
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
