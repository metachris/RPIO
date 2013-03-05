import RPIO.PWM as PWM

GPIO = 17
CHANNEL = 0

PWM.set_loglevel(PWM.LOG_LEVEL_DEBUG)

PWM.setup()
PWM.init_channel(CHANNEL)
PWM.print_channel(CHANNEL)

PWM.add_channel_pulse(CHANNEL, GPIO, 0, 50)
PWM.add_channel_pulse(CHANNEL, GPIO, 100, 50)
