import RPIO.PWM as PWM


# Our PWM settings
GPIO = 17
PERIOD_TIME_US = 2000  # 2000us
PULSE_WIDTH_INCREMENTS_US = 10
PULSE_WIDTH = 100      # = 1000us

# Start PWM on DMA channel 0
PWM.setup(PULSE_WIDTH_INCREMENTS_US)
PWM.init_channel(0, GPIO, PERIOD_TIME_US)
PWM.set_channel_pulse(0, PULSE_WIDTH)
