"""
This file is part of RPIO.

License: GPLv3+
Author: Chris Hager <chris@linuxuser.at>
URL: https://github.com/metachris/RPIO

Flexible PWM via DMA for the Raspberry Pi. Multiple DMA channels are
supported. You can use PCM instead of PWM with the "--pcm" argument.

Example:

    import RPIO.PWM as PWM

    GPIO = 17
    CHANNEL = 0

    PWM.setup()
    PWM.init_channel(CHANNEL)
    PWM.set_loglevel(PWM.LOG_LEVEL_DEBUG)

    PWM.add_channel_pulse(CHANNEL, GPIO, 0, 50)
    PWM.add_channel_pulse(CHANNEL, GPIO, 100, 50)
    ...

    PWM.clear_channel_pulses(CHANNEL)
"""
import _PWM

# Grab constants from C module
DELAY_VIA_PWM = _PWM.DELAY_VIA_PWM
DELAY_VIA_PCM = _PWM.DELAY_VIA_PCM
LOG_LEVEL_DEBUG = _PWM.LOG_LEVEL_DEBUG
LOG_LEVEL_ERRORS = _PWM.LOG_LEVEL_ERRORS
PERIOD_TIME_US_DEFAULT = _PWM.PERIOD_TIME_US_DEFAULT
PULSE_WIDTH_INCREMENT_GRANULARITY_US_DEFAULT = \
        _PWM.PULSE_WIDTH_INCREMENT_GRANULARITY_US_DEFAULT
VERSION = _PWM.VERSION


def setup(pulse_incr_us=PULSE_WIDTH_INCREMENT_GRANULARITY_US_DEFAULT, \
        delay_hw=DELAY_VIA_PWM):
    """
    Setup needs to be called once before working with any channels.

    Optional Parameters:
        pulse_incr_us: the pulse width increment granularity (deault=10us)
        delay_hw: either PWM.DELAY_VIA_PWM (default) or PWM.DELAY_VIA_PCM
    """
    _PWM.setup(pulse_incr_us, delay_hw)


def cleanup():
    """ Stops all PWM and DMA actvity """
    _PWM.cleanup()


def init_channel(channel, period_time_us=PERIOD_TIME_US_DEFAULT):
    """ Setup a channel with a specific period time (in microseconds [us]) """
    _PWM.init_channel(channel, period_time_us)


def clear_channel_pulses(channel):
    """ Clears a channel of all pulses """
    _PWM.clear_channel_pulses(channel)


# def init_channel_with_freq(channel, gpio, freq_hz):
#     """
#     Setup a channel for a specific GPIO with a frequency in Hz. You can
#     change the pulse-width within the frequency with set_channel_pulse(..).
#     """
#     _PWM.init_channel(channel, gpio, 1000000 / freq_hz)


def add_channel_pulse(channel, gpio, width_start, width):
    """ Add a pulse within the period for a specific GPIO to a channel """
    _PWM.add_channel_pulse(channel, gpio, width_start, width)


def print_channel(channel):
    """ Print info about a specific channel to stdout """
    _PWM.print_channel(channel)


def set_loglevel(level):
    """ Sets the loglevel for the PWM module """
    _PWM.set_loglevel(level)
