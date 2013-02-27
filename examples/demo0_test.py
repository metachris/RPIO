import logging
log_format = '%(levelname)s | %(asctime)-15s | %(message)s'
logging.basicConfig(format=log_format, level=logging.DEBUG)
import RPIO


def socket_callback(socket, val):
    print("socket %s: '%s'" % (socket.fileno(), val))
    socket.send("echo: %s\n" % val)


def gpio_callback(gpio_id, val):
    print("gpio %s: %s" % (gpio_id, val))


RPIO.add_interrupt_callback(17, gpio_callback)
RPIO.add_tcp_callback(8080, socket_callback)
RPIO.wait_for_interrupts()
