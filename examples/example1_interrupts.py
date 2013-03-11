#import logging
#log_format = '%(levelname)s | %(asctime)-15s | %(message)s'
#logging.basicConfig(format=log_format, level=logging.DEBUG)

import RPIO


def gpio_callback(gpio_id, val):
    print("gpio %s: %s" % (gpio_id, val))


def socket_callback(socket, val):
    print("socket %s: '%s'" % (socket.fileno(), val))
    socket.send("echo: %s\n" % val)
    RPIO.close_tcp_client(socket.fileno())


# Add two GPIO interrupt callbacks (second one with a debouce timeout of 100ms)
RPIO.add_interrupt_callback(17, gpio_callback)
RPIO.add_interrupt_callback(14, gpio_callback, edge='rising', \
        debounce_timeout_ms=100)

# Add one TCP interrupt callback (opens socket server at port 8080)
RPIO.add_tcp_callback(8080, socket_callback)

# Wait for interrupts indefinitely, and clean up before quitting
try:
    RPIO.wait_for_interrupts()
finally:
    RPIO.cleanup()
