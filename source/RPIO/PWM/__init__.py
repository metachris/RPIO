"""
This file is part of RPIO.

License: GPLv3+
Author: Chris Hager <chris@linuxuser.at>
URL: https://github.com/metachris/RPIO

Flexible PWM via DMA for the Raspberry Pi. Multiple DMA channels are
supported. You can use PCM instead of PWM with the "--pcm" argument.

Example:

    import RPIO.PWM as PWM
    PWM.setup()
    PWM.init_channel(0, 17, 2000)
    PWM.set_channel_pulse(0, 100)
"""
import _PWM

DELAY_VIA_PWM = 0
DELAY_VIA_PCM = 1

VERSION = _PWM.VERSION


def setup(pulse_incr_us=10, delay_hw=DELAY_VIA_PWM):
    """
    Setup needs to be called once before working with any channels.

    Parameters:
        pulse_incr_us: the pulse width increment granularity
        delay_hw: either PWM.DELAY_VIA_PWM (default) or PWM.DELAY_VIA_PCM
    """
    _PWM.setup(pulse_incr_us, delay_hw)


def cleanup():
    """ Stops all PWM and DMA actvity """
    _PWM.cleanup()


def init_channel(channel, gpio, period_time_us):
    """
    Setup a channel for a specific GPIO with a specific period time
    (in microseconds [us])
    """
    _PWM.init_channel(channel, gpio, period_time_us)


def init_channel_with_freq(channel, gpio, freq_hz):
    """
    Setup a channel for a specific GPIO with a frequency in Hz. You can
    change the pulse-width within the frequency with set_channel_pulse(..).
    """
    _PWM.init_channel(channel, gpio, 1000000 / freq_hz)


def set_channel_pulse(channel, width):
    """
    Set the pulse-width of a channel to a specific number of increments
    """
    _PWM.set_channel_pulse(channel, width)


def print_channel(channel):
    """ Print info about a specific channel to stdout """
    _PWM.print_channel(channel)
