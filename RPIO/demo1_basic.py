"""
Example of using interrupts and RPIO to react to state-changes on
gpio pins 23, 24 and 25. Setting up logging before importing RPIO
enables log output of the module.
"""
import logging
logging.basicConfig(format='%(levelname)s | %(asctime)s | %(message)s', \
        datefmt='%m/%d/%Y %I:%M:%S %p', level=logging.DEBUG)
import RPIO


def handle_interrupt(gpio_id, val):
    print("New value for GPIO %s: %s" % (gpio_id, val))


def start():
    RPIO.add_interrupt_callback(23, handle_interrupt, edge='rising')
    RPIO.add_interrupt_callback(24, handle_interrupt, edge='falling')
    RPIO.add_interrupt_callback(25, handle_interrupt, edge='both')
    RPIO.wait_for_interrupts()


start()
