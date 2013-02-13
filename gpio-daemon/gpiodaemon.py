#!/usr/bin/env python
"""
Simple unix socket daemon (based on tornado) to execute GPIO commands.
Comes with a lot of goodies, such as user-defined commands, yaml-based
configuration file, scheduled (deferred) tasks, ...

The configuration file can be found at `gpiodaemon/config.yaml`. Edit
this to your project specific gpio needs!
"""
import os
import sys
import signal
import socket
import traceback
import logging
from os import getpid, remove, kill
from optparse import OptionParser
from time import sleep

from tornado.ioloop import IOLoop
from tornado.netutil import TCPServer

from daemon import Daemon
import gpiomanager


LOGFILE = "/opt/rpi-django/logs/gpiodaemon.log"
LOGLEVEL = logging.DEBUG

CONFIG_FILE = os.path.join(os.path.abspath(os.path.dirname(__file__)), "config.yaml")

PORT = 9101
PIDFILE = "/tmp/gpiodaemon.pid"


# Setup Logging
logging.basicConfig(filename=LOGFILE, format='%(levelname)s | %(asctime)s | %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p')
logger = logging.getLogger(__name__)
logger.setLevel(LOGLEVEL)


# Catch SIGINT to shut the daemon down (eg. via $ kill -s SIGINT [proc-id])
def signal_handler(signal, frame):
    sys.exit(0)
signal.signal(signal.SIGINT, signal_handler)


# Each connected client gets a TCPConnection object
class TCPConnection(object):
    def __init__(self, gpio, stream, address):
        logger.debug('- new connection from %s' % repr(address))
        self.GPIO = gpio
        self.stream = stream
        self.address = address
        self.stream.set_close_callback(self._on_close)
        self.stream.read_until('\n', self._on_read_line)

    def _on_read_line(self, data):
        data = data.strip()
        if not data or data == "quit":
            self.stream.close()
            return

        # Process input
        response = self.GPIO.handle_cmd(data)
        if response:
            self.stream.write("%s\n" % response.strip())

        # Continue reading on this connection
        self.stream.read_until('\n', self._on_read_line)

    def _on_write_complete(self):
        pass

    def _on_close(self):
        logger.debug('- client quit %s' % repr(self.address))


# The main server class
class GPIOServer(TCPServer):
    def __init__(self, gpio, io_loop=None, ssl_options=None, **kwargs):
        self.GPIO = gpio
        TCPServer.__init__(self, io_loop=io_loop, ssl_options=ssl_options, **kwargs)

    def handle_stream(self, stream, address):
        TCPConnection(self.GPIO, stream, address)


# Helper to reload config of a running daemon
def daemon_reload():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.connect(("localhost", PORT))
        sock.sendall("reload\n\n")  # second newline (empty packet) terminates the connection server-side
    finally:
        sock.close()


class GPIODaemon(Daemon):
    def run(self):
        try:
            logger.info("Starting GPIODaemon...")
            GPIO = gpiomanager.GPIO(logger=logger, configfile=CONFIG_FILE)
            gpio_server = GPIOServer(GPIO)
            gpio_server.listen(PORT)

            # Loop here
            IOLoop.instance().start()

        except SystemExit:
            logger.info("Shutting down via signal")

        except Exception as e:
            logger.exception(e)

        finally:
            try:
                GPIO.cleanup()

            except Exception as e:
                logger.exception(e)

            finally:
                logger.info("GPIODaemon stopped")


# Console start
if __name__ == '__main__':
    # Prepare help and options
    usage = """usage: %prog start|stop|restart|reload"""
    desc="""GPIO-Daemon is little program to help dealing with/programming the
GPIO ports on the Raspberry pi via a socket interface (eg. telnet). The
daemon listens on port %s for TCP connections.""" % PORT
    parser = OptionParser(usage=usage, description=desc)
    (options, args) = parser.parse_args()

    # Setup daemon
    daemon = GPIODaemon(PIDFILE)

    # Process startup argument
    if not args:
        parser.print_help()

    elif "start" == args[0]:
        daemon.start()
        print "GPIO daemon started."

    elif "stop" == args[0]:
        daemon.stop()

    elif "reload" == args[0]:
        daemon_reload()

    elif "restart" == args[0]:
        daemon.restart()

    else:
        parser.print_help()
