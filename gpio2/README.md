GPIO2 is an extension of RPi.GPIO to easily use interrupts.

Interrupts are used to receive notifications from the kernel when GPIO state 
changes occur. Advantages include minimized cpu consumption, very fast
notification times, and the ability to trigger on specific edge transitions
(`'rising|falling|both'`). Here is a very simple example:

    import GPIO2

    def do_something(gpio_id, value):
        print("New value for GPIO %s: %s" % (gpio_id, value))

    GPIO2.add_interrupt_callback(17, do_something, edge='rising')
    GPIO2.add_interrupt_callback(18, do_something, edge='falling')
    GPIO2.add_interrupt_callback(19, do_something, edge='both')
    GPIO2.wait_for_interrupts()

If you want to receive a callback inside a Thread (which won't block anything
else on the system), set `threaded_callback` to True when adding an interrupt-
callback. Here is an example:

    GPIO2.add_interrupt_callback(17, do_something, edge='rising',
            threaded_callback=True)

Make sure to double-check the value returned from the interrupt, since it
is not necessarily corresponding to the edge (eg. 0 may come in as value,
even if edge="rising").

To remove all callbacks from a certain gpio pin, use
`GPIO2.del_interrupt_callback(gpio_id)`. To stop the `wait_for_interrupts()`
loop you can either set `GPIO2.is_waiting_for_interrupts` to `False`, or call
`GPOP2.stop_waiting_for_interrupts()`.

If an interrupt occurs while your callback function does something blocking
(like `time.sleep()` outside a thread), events will not arrive until you
release the block. Only one process can receive interrupts for a specific GPIO
pin, since the read on `/sys/class/gpio/gpio<N>/value` destroys the value for
subsequent reads. 

On the Raspberry Pi interrupts work via the `/sys/class/gpio` kernel 
interface, waiting for value changes with `epoll`. 


Links
-----
* https://github.com/metachris/raspberrypi-utils
* http://pypi.python.org/pypi/RPi.GPIO
* http://www.kernel.org/doc/Documentation/gpio.txt


Feedback 
--------
Chris Hager (<chris@linuxuser.at>)