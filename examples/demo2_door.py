"""
Example of using interrupts to react when someone rings the door bell (input
via GPIO 23). This script unlocks the door for a few seconds via GPIO 22 when
someone rings twice within 0.5 seconds.
"""
from time import sleep
from time import time
from urllib import urlopen
from threading import Thread

import logging
log_format = '%(levelname)s | %(asctime)-15s | %(message)s'
logging.basicConfig(format=log_format, level=logging.DEBUG)
import RPIO

# GPIO-22 goes to a relay which unlocks the door
GPIO2.setup(22, GPIO2.OUT)

# Memory for time when bell rang last
last_bell_ring = None


def handle_door_bell_ring(gpio_id, val):
    # We don't need the gpio_id and val the callback provides since we get
    # notified only on rising edges anyway.
    if not val:
        # filter out 0 (we want 1 only)
        return

    t = time()
    print "Someone rang the door bell."

    # Check timing and unlock door if someone rings twice within 0.5 sec.
    global last_bell_ring
    if last_bell_ring:
        time_since_last_bell_ring_sec = t - last_bell_ring
        print "- time since last ring: %.2f seconds" % \
                time_since_last_bell_ring_sec
        if time_since_last_bell_ring_sec <= 0.5:
            print "- unlocking for 5 seconds"
            GPIO2.output(22, GPIO2.HIGH)
            sleep(3)
            GPIO2.output(22, GPIO2.LOW)

            # Add log entry via http-request to local webserver
            # url_log = ("http://127.0.0.1/log_add_event?"
            #        "type=door_bell_twice&value=on")
            # Thread(taget=urlopen, args=(url_log,)).start()

    # Save time of last ring
    last_bell_ring = t

# Main loop. Blocks at `wait_for_interrupts()`.
RPIO.add_interrupt_callback(23, handle_door_bell_ring, edge='rising')
RPIO.wait_for_interrupts()
