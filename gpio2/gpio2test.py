# Example of reacting to state-changes on input pins 23, 24 and 25
# by using interrupts and GPIO2. Original code from 
# http://learn.adafruit.com/playing-sounds-and-using-buttons-with-raspberry-pi/code
import GPIO2

def handle_interrupt(gpio_id, val):
    print "New value for GPIO %s: %s" % (gpio_id, val)

def start():
    GPIO2.add_interrupt_callback(23, handle_interrupt, edge='rising')
    GPIO2.add_interrupt_callback(24, handle_interrupt, edge='falling')
    GPIO2.add_interrupt_callback(25, handle_interrupt, edge='both')
    GPIO2.wait_for_interrupts()

start()
