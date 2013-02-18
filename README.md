Python tools to simplify working with the Raspberry Pi and it's GPIO port. All source code in
this repository is released under the MIT license.


**[RPIO](https://github.com/metachris/raspberrypi-utils/tree/master/RPIO)**

Extension of [RPi.GPIO](http://pypi.python.org/pypi/RPi.GPIO) which can handle interrupts.
Works with Python 2.x and 3.x. The easiest way to install RPIO is via pip:

    sudo pip install RPIO


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

    import RPIO

    def do_something(gpio_id, value):
        print("New value for GPIO %s: %s" % (gpio_id, value))

    RPIO.add_interrupt_callback(17, do_something, edge='rising')
    RPIO.add_interrupt_callback(18, do_something, edge='falling')
    RPIO.add_interrupt_callback(19, do_something, edge='both')
    RPIO.wait_for_interrupts()


Links
-----
* http://pypi.python.org/pypi/RPi.GPIO
* http://www.kernel.org/doc/Documentation/gpio.txt
* [Raspberry Pi Revision Identification](http://www.raspberrypi.org/phpBB3/viewtopic.php?f=63&t=32733)


Feedback 
--------
Chris Hager (<chris@linuxuser.at>)