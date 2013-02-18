# Example of using interrupts and GPIO2 to react to state-changes on
# gpio pins 23, 24 and 25
import GPIO2


def handle_interrupt(gpio_id, val):
    print("New value for GPIO %s: %s" % (gpio_id, val))


def start():
    GPIO2.add_interrupt_callback(23, handle_interrupt, edge='rising')
    GPIO2.add_interrupt_callback(24, handle_interrupt, edge='falling')
    GPIO2.add_interrupt_callback(25, handle_interrupt, edge='both')
    GPIO2.wait_for_interrupts()


start()
