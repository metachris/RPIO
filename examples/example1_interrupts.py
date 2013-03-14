"""
Example of how to use GPIO and TCP interrupts with RPIO.
RPIO Documentation: http://pythonhosted.org/RPIO
"""
import RPIO


def gpio_callback(gpio_id, val):
    print("gpio %s: %s" % (gpio_id, val))


def socket_callback(socket, val):
    print("socket %s: '%s'" % (socket.fileno(), val))
    socket.send("echo: %s\n" % val)
    RPIO.close_tcp_client(socket.fileno())


# Two GPIO interrupt callbacks (second one with a debouce timeout of 100ms)
RPIO.add_interrupt_callback(17, gpio_callback)
RPIO.add_interrupt_callback(14, gpio_callback, edge='rising', \
        debounce_timeout_ms=100)

# One TCP interrupt callback (opens socket server at port 8080)
RPIO.add_tcp_callback(8080, socket_callback)

# Starts waiting for interrupts (exit with Ctrl+C)
RPIO.wait_for_interrupts()
