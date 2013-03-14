"""
This example uses lower-level PWM control methods of RPIO.PWM. The default
settings include a subcycle time of 20ms and a pulse-width increment
granularity of 10us.

RPIO Documentation: http://pythonhosted.org/RPIO
"""
import RPIO.PWM as PWM

GPIO = 17
CHANNEL = 0

PWM.set_loglevel(PWM.LOG_LEVEL_DEBUG)

PWM.setup()
PWM.init_channel(CHANNEL)
PWM.print_channel(CHANNEL)

PWM.add_channel_pulse(CHANNEL, GPIO, 0, 50)
PWM.add_channel_pulse(CHANNEL, GPIO, 100, 50)
