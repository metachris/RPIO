"""
This file is part of RPIO.

Author: Chris Hager <chris@linuxuser.at>
Docs: http://pythonhosted.org/RPIO
URL: https://github.com/metachris/RPIO
License: GPLv3+

Flexible PWM via DMA for the Raspberry Pi. Multiple DMA channels are
supported. You can also use PCM instead of PWM.

Example:

    import RPIO.PWM as PWM
    GPIO = 17
    FREQ_HZ = 440
    p = PWM.PulseGenerator()
    p.set_frequency(GPIO, FREQ_HZ)

"""
import _PWM

# Constants from pwm.c
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
    _PWM.setup(pulse_incr_us, delay_hw)


def cleanup():
    """ Stops all PWM and DMA actvity """
    _PWM.cleanup()


def init_channel(channel, subcycle_time_us=SUBCYCLE_TIME_US_DEFAULT):
    """ Setup a channel with a specific subcycle time [us] """
    _PWM.init_channel(channel, subcycle_time_us)


def clear_channel_pulses(channel):
    """ Clears a channel of all pulses """
    _PWM.clear_channel_pulses(channel)


def add_channel_pulse(channel, gpio, width_start, width):
    """ Add a pulse within the subcycle for a specific GPIO to a channel """
    _PWM.add_channel_pulse(channel, gpio, width_start, width)


def print_channel(channel):
    """ Print info about a specific channel to stdout """
    _PWM.print_channel(channel)


def set_loglevel(level):
    """ Sets the loglevel for the PWM module """
    _PWM.set_loglevel(level)


#
# Helpers
#
class PulseGenerator(object):
    """
    This class sets a specific output frequency for a GPIO. By default
    DMA channel 0 is used, but you can use any one you like (0..14).

    Pulse width granularity is 10us by default, but you can set this
    manually for all DMA channels with the setup(..) argument
    `pulse_width_increment_granularity_us`.
    """
    freq_max = None
    subcycle_time_us = None
    subcycle_time_s = None
    incr_granularity_us = None
    channels_initialized = 0  # bitfield of initialized DMA channels
    gpios_initialized = 0  # bitfield to keep track of already added GPIOs

    def __init__(self, pulse_width_increment_granularity_us=\
            PULSE_WIDTH_INCREMENT_GRANULARITY_US_DEFAULT,
            subcycle_time_us=SUBCYCLE_TIME_US_DEFAULT,
            delay_hw=DELAY_VIA_PWM):
        _PWM.setup(pulse_width_increment_granularity_us, delay_hw)

        self.incr_granularity_us = pulse_width_increment_granularity_us
        self.freq_max = 1000000 / (self.incr_granularity_us * 2)

        self.subcycle_time_us = subcycle_time_us
        self.subcycle_time_s = subcycle_time_us / 1000000.0

        print "max freq: %sHz" % self.freq_max
        print "subcycle time: %ss (%sus)" % (self.subcycle_time_s, \
                self.subcycle_time_us)
        print "increment granularity: %sus" % self.incr_granularity_us
        print "--"

    def set_frequency(self, gpio, frequency_hz, pulse_width='50%', \
            dma_channel=0):
        """
        This method sets a specific output frequency for a GPIO. Will
        initialize the DMA channel on first use.
        """
        if int(frequency_hz) > self.freq_max:
            raise Exception("Cannot set frequency > subcycle time")

        print "Setting freq to %sHz for GPIO %s on DMA channel %s" % \
                (frequency_hz, gpio, dma_channel)

        # Setup DMA channel if first use
        if not self.channels_initialized & 1 << dma_channel:
            _PWM.init_channel(dma_channel, self.subcycle_time_us)
            self.channels_initialized |= 1 << dma_channel

        freq_in_subcycle = frequency_hz * self.subcycle_time_s
        print "frequency in subcycle: %sHz" % freq_in_subcycle

        freq_time_us = self.subcycle_time_us / freq_in_subcycle
        print "frequency time: %sus" % freq_time_us

        if freq_time_us < self.incr_granularity_us:
            raise Exception(("Cannot set lower frequency time than increment-"
                    "granularity (%sus)") % self.incr_granularity_us)

        print "--"
        freq_time_steps = int(freq_time_us / self.incr_granularity_us)
        print "frequency width per subcycle: %s" % freq_time_steps

        _pulse_width = None
        if "%" in pulse_width:
            pulse_width_percent = int(pulse_width.strip(" %"))
            if pulse_width_percent < 0 or pulse_width_percent > 99:
                raise Exception("Invalid pulse width: %s%%" % \
                        pulse_width_percent)
            _pulse_width = int(freq_time_steps * (pulse_width_percent * 0.01))
        elif "us" in pulse_width:
            _pulse_width = int(pulse_width.strip("us")) / \
                    self.incr_granularity_us
            if _pulse_width < 1:
                raise Exception("Invalid pulse width: %s%%" % \
                        pulse_width_percent)

        print "pulse width: %s steps" % _pulse_width

        num_pulses_per_subcycle = (self.subcycle_time_us / \
                self.incr_granularity_us) / freq_time_steps
        print "pulses per subcycle: %s" % num_pulses_per_subcycle
        print "actual output frequency: %sHz" % (num_pulses_per_subcycle / \
                self.subcycle_time_s)

        for i in range(num_pulses_per_subcycle):
            pulse_start_step = _pulse_width * i * 2
            add_channel_pulse(dma_channel, gpio, pulse_start_step, \
                    _pulse_width)
