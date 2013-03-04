import time
import RPIO.PWM as PWM
import RPIO.PWM.Notes

GPIO = 17
PERIOD_TIME_US = 2000  # 2000us
PULSE_WIDTH_INCREMENTS_US = 10


# Setup PWM for all channes
PWM.setup(PULSE_WIDTH_INCREMENTS_US)

# To use PCM instead of PWM for the timings:
#PWM.setup(PULSE_WIDTH_INCREMENTS_US, delay_hw=PWM.DELAY_VIA_PCM)


# Initialize DMA channel 0 for GPIO 17
PWM.init_channel(0, GPIO, PERIOD_TIME_US)

# Alternatively you can init a channel with a frequency:
# PWM.init_channel_with_freq(0, GPIO, RPIO.PWM.Notes.A4)


# Now set various pulse widths. Note that pulse widths are multiplied
# by PULSE_WIDTH_INCREMENTS_US to get the pulse time in microseconds.
PWM.set_channel_pulse(0, 100)  # 1000 us
time.sleep(10)

PWM.set_channel_pulse(0, 10)   # 100 us
time.sleep(10)

PWM.set_channel_pulse(0, 1)    # 10 us
time.sleep(10)
