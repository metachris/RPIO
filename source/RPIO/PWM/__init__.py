# -*- coding: utf-8 -*-
#
# This file is part of RPIO.
#
# Copyright
#
#     Copyright (C) 2013 Chris Hager <chris@linuxuser.at>
#
# License
#
#     This program is free software: you can redistribute it and/or modify
#     it under the terms of the GNU Lesser General Public License as published
#     by the Free Software Foundation, either version 3 of the License, or
#     (at your option) any later version.
#
#     This program is distributed in the hope that it will be useful,
#     but WITHOUT ANY WARRANTY; without even the implied warranty of
#     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#     GNU Lesser General Public License for more details at
#     <http://www.gnu.org/licenses/lgpl-3.0-standalone.html>
#
# Documentation
#
#     http://pythonhosted.org/RPIO
#
"""
Flexible PWM via DMA for the Raspberry Pi. Supports pulse width granularities
of down to 1µs, multiple DMA channels, multiple GPIOs per channel, timing by
PWM (default) or PCM and more. RPIO.PWM is BETA; feedback highly appreciated.

You can directly access the low-level methods via PWM.init_channel(), etc. as
well as several helpers such as the PWM.Servo class. For more information take
a look at pythonhosted.org/RPIO as well as the source code at
https://github.com/metachris/RPIO/blob/master/source/c_pwm

Example of using `PWM.Servo`:

    servo = RPIO.PWM.Servo()

    # Set servo on GPIO17 to 1200µs (1.2ms)
    servo.set_servo(17, 1200)

    # Set servo on GPIO17 to 2000µs (2.0ms)
    servo.set_servo(17, 2000)

    # Clear servo on GPIO17
    servo.stop_servo(17)

Example of using the low-level methods:

    PWM.setup()
    PWM.init_channel(0)
    PWM.print_channel(0)
    PWM.add_channel_pulse(0, 17, 0, 50)
    ...
    PWM.clear_channel_gpio(0, 17)
    ...
    PWM.cleanup()
"""
from RPIO.PWM import _PWM

#
# Constants from pwm.c
#
DELAY_VIA_PWM = _PWM.DELAY_VIA_PWM
DELAY_VIA_PCM = _PWM.DELAY_VIA_PCM
LOG_LEVEL_DEBUG = _PWM.LOG_LEVEL_DEBUG
LOG_LEVEL_ERRORS = _PWM.LOG_LEVEL_ERRORS
SUBCYCLE_TIME_US_DEFAULT = _PWM.SUBCYCLE_TIME_US_DEFAULT
PULSE_WIDTH_INCREMENT_GRANULARITY_US_DEFAULT = \
        _PWM.PULSE_WIDTH_INCREMENT_GRANULARITY_US_DEFAULT
VERSION = _PWM.VERSION


#
# Methods from pwm.c
#
def setup(pulse_incr_us=PULSE_WIDTH_INCREMENT_GRANULARITY_US_DEFAULT, \
        delay_hw=DELAY_VIA_PWM):
    """
    Setup needs to be called once before working with any channels.

    Optional Parameters:
        pulse_incr_us: the pulse width increment granularity (deault=10us)
        delay_hw: either PWM.DELAY_VIA_PWM (default) or PWM.DELAY_VIA_PCM
    """
    return _PWM.setup(pulse_incr_us, delay_hw)


def cleanup():
    """ Stops all PWM and DMA actvity """
    return _PWM.cleanup()


def init_channel(channel, subcycle_time_us=SUBCYCLE_TIME_US_DEFAULT):
    """ Setup a channel with a specific subcycle time [us] """
    return _PWM.init_channel(channel, subcycle_time_us)


def clear_channel(channel):
    """ Clears a channel of all pulses """
    return _PWM.clear_channel(channel)


def clear_channel_gpio(channel, gpio):
    """ Clears one specific GPIO from this DMA channel """
    return _PWM.clear_channel_gpio(channel, gpio)


def add_channel_pulse(dma_channel, gpio, start, width):
    """
    Add a pulse for a specific GPIO to a dma channel subcycle. `start` and
    `width` are multiples of the pulse-width increment granularity.
    """
    return _PWM.add_channel_pulse(dma_channel, gpio, start, width)


def print_channel(channel):
    """ Print info about a specific channel to stdout """
    return _PWM.print_channel(channel)


def set_loglevel(level):
    """
    Sets the loglevel for the PWM module to either PWM.LOG_LEVEL_DEBUG for all
    messages, or to PWM.LOG_LEVEL_ERRORS for only fatal error messages.
    """
    return _PWM.set_loglevel(level)


def is_setup():
    """ Returns 1 if setup(..) has been called, else 0 """
    return _PWM.is_setup()


def is_channel_initialized(channel):
    """ Returns 1 if this channel has been initialized, else 0 """
    return _PWM.is_channel_initialized(channel)


def get_pulse_incr_us():
    """ Returns the currently set pulse width increment granularity in us """
    return _PWM.get_pulse_incr_us()


def get_channel_subcycle_time_us(channel):
    """ Returns this channels subcycle time in us """
    return _PWM.get_channel_subcycle_time_us(channel)


class Servo:
    """
    This class is a helper for using servos on any number of GPIOs.
    The subcycle time is set to the servo default of 20ms, but you can
    adjust this to your needs via the `Servo.__init__(..)` method.

    Example:

        servo = RPIO.PWM.Servo()

        # Set servo on GPIO17 to 1200µs (1.2ms)
        servo.set_servo(17, 1200)

        # Set servo on GPIO17 to 2000µs (2.0ms)
        servo.set_servo(17, 2000)

        # Clear servo on GPIO17
        servo.stop_servo(17)
    """
    _subcycle_time_us = None
    _dma_channel = None

    def __init__(self, dma_channel=0, subcycle_time_us=20000, \
            pulse_incr_us=10):
        """
        Makes sure PWM is setup with the correct increment granularity and
        subcycle time.
        """
        self._dma_channel = dma_channel
        self._subcycle_time_us = subcycle_time_us
        if _PWM.is_setup():
            _pw_inc = _PWM.get_pulse_incr_us()
            if not pulse_incr_us == _pw_inc:
                raise AttributeError(("Error: PWM is already setup with pulse-"
                        "width increment granularity of %sus instead of %sus")\
                         % (_pw_inc, self.pulse_incr_us))
        else:
            setup(pulse_incr_us=pulse_incr_us)

    def set_servo(self, gpio, pulse_width_us):
        """
        Sets a pulse-width on a gpio to repeat every subcycle
        (by default every 20ms).
        """
        # Make sure we can set the exact pulse_width_us
        _pulse_incr_us = _PWM.get_pulse_incr_us()
        if pulse_width_us % _pulse_incr_us:
            # No clean division possible
            raise AttributeError(("Pulse width increment granularity %sus "
                    "cannot divide a pulse-time of %sus") % (_pulse_incr_us,
                    pulse_width_us))

        # Initialize channel if not already done, else check subcycle time
        if _PWM.is_channel_initialized(self._dma_channel):
            _subcycle_us = _PWM.get_channel_subcycle_time_us(self._dma_channel)
            if _subcycle_us != self._subcycle_time_us:
                raise AttributeError(("Error: DMA channel %s is setup with a "
                        "subcycle_time of %sus (instead of %sus)") % \
                        (self._dma_channel, _subcycle_us, 
                            self._subcycle_time_us))
        else:
            init_channel(self._dma_channel, self._subcycle_time_us)

        # Add pulse for this GPIO
        add_channel_pulse(self._dma_channel, gpio, 0, \
                int(pulse_width_us / _pulse_incr_us))

    def stop_servo(self, gpio):
        """ Stops servo activity for this gpio """
        clear_channel_gpio(self._dma_channel, gpio)
