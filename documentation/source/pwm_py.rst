.. _ref-rpio-pwm-py:

``RPIO.PWM``, PWM via DMA for the Raspberry Pi
==============================================

``RPIO.PWM`` enables very accurate PWM for the Raspberry Pi, using the DMA bus and the onboard
PWM module for semi-hardware pulse width modulation. Pulse-width can be set as low as 1µs, which
equates to 500kHz max. ``RPIO.PWM`` is not yet part of a release package, but you can get it from
the dev branch on Github::

    $ git clone https://github.com/metachris/RPIO.git -b dev
    $ cd RPIO
    $ python setup.py build


Examples
--------

Example of using `PWM.Servo`::

    servo = RPIO.PWM.Servo()

    # Set servo on GPIO17 to 1200µs (1.2ms)
    servo.set_servo(17, 1200)

    # Set servo on GPIO17 to 2000µs (2.0ms)
    servo.set_servo(17, 2000)

    # Clear servo on GPIO17
    servo.stop_servo(17)


Example of using the low-level methods::

    PWM.setup()
    PWM.init_channel(0)
    PWM.print_channel(0)
    PWM.add_channel_pulse(0, 17, 0, 50)
    ...
    PWM.clear_channel_gpio(0, 17)
    ...
    PWM.cleanup()


Under the hood
--------------

