Python tools to simplify working with the Raspberry Pi and it's GPIO port. All source code in
this repository is released under the MIT license.


**GPIO2.py**

Extension of [RPi.GPIO](http://pypi.python.org/pypi/RPi.GPIO) which can handle interrupts.


**gpiodaemon.py**

Socket daemon which can handle scheduled task management (run a command in <n>
seconds, eg. to turn something off after a certain amount of time), and
accepts user defined commands (eg. `led on` instead of `set 17 HIGH`). Custom
commands and pin setup are defined in `config.yaml`. The deamon listens on
port 9101. Requires the [tornado](http://pypi.python.org/pypi/tornado) and
[pyyaml](http://pypi.python.org/pypi/PyYAML).


**rpi\_detect\_model.py**

Detects a Raspberry's model and manufacturer, and makes the attributes
easily accessible.


**sdbackup.sh**

Backup boot and root partition of a linux SD card into .tar files.


Interrupts
----------
Interrupts can be used to receive notifications from the kernel when GPIO state 
changes occur. This has the advantages of requiring almost zero cpu consumption
and very fast notification times, as well as allowing to easily monitor
specific transitions via `edge='rising|falling|both'`. Here is an example:

***Example: Interrupts and GPIO2***

    import GPIO2

    def handle_interrupt(gpio_id, value):
        print "New value for GPIO %s: %s" % (gpio_id, value)

    GPIO2.add_interrupt_callback(23, handle_interrupt, edge='rising')
    GPIO2.add_interrupt_callback(24, handle_interrupt, edge='falling')
    GPIO2.add_interrupt_callback(25, handle_interrupt, edge='both')
    GPIO2.wait_for_interrupts()

GPIO2 can also start the callback inside a Thread; just set the parameter
`threaded_callback` to True when adding an interrupt-callback:

    GPIO2.add_interrupt_callback(23, handle_interrupt, edge='rising', threaded_callback=True)

If an interrupt occurs while your callback function does something blocking
(like `time.sleep()` outside a thread), events will not arrive until you
release the block. Only one process can receive interrupts for a specific GPIO
pin, since the read on `/sys/class/gpio/gpio<N>/value` destroys the value for
subsequent reads. 

On the Raspberry Pi interrupts work via the `/sys/class/gpio` kernel 
interface, waiting for value changes with `epoll`. 


Todo
----
- [ ] `GPIO.input(...)` can set a pullup/pulldown resistor, which is not yet part
of this interrupt extension (since there is no option for it in /sys/class/gpio/...).
Note to self: A possible solution is to replicate the function from `RPi.GPIO.input()`. 


Links
-----
* http://pypi.python.org/pypi/RPi.GPIO
* http://www.kernel.org/doc/Documentation/gpio.txt
* [Raspberry Pi Revision Identification](http://www.raspberrypi.org/phpBB3/viewtopic.php?f=63&t=32733)


Feedback 
--------
Chris Hager (<chris@linuxuser.at>)