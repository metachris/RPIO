"""
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
    _PWM.setup(pulse_incr_us, delay_hw)


def cleanup():
    """ Manually stop all PWM and DMA actvity """
    _PWM.cleanup()


def init_channel(channel, gpio, period_time_us):
    """
    Setup a channel for a specific GPIO with a specific period time
    (in microseconds [us])
    """
    _PWM.init_channel(channel, gpio, period_time_us)


def set_channel_pulse(channel, width):
    """
    Set the pulse-width of a channel to a specific number of increments
    """
    _PWM.set_channel_pulse(channel, width)


def print_channel(channel):
    _PWM.print_channel(channel)
