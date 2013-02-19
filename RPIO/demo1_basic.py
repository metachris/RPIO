"""
Example of using interrupts and RPIO to react to state-changes on gpio pins.
Setting up logging before importing RPIO enables its log output.
"""
import logging
log_format = '%(levelname)s | %(asctime)-15s | %(message)s'
logging.basicConfig(format=log_format, level=logging.DEBUG)
import RPIO


def handle_interrupt(gpio_id, val):
    logging.info("New value for GPIO %s: %s" % (gpio_id, val))


RPIO.add_interrupt_callback(23, handle_interrupt, edge='rising')
RPIO.add_interrupt_callback(24, handle_interrupt, edge='falling')
RPIO.add_interrupt_callback(25, handle_interrupt, edge='both',
        threaded_callback=True)

try:
    RPIO.wait_for_interrupts()

except KeyboardInterrupt:
    RPIO.cleanup()
