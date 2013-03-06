"""
This example demonstrates how to easily create frequencies with specific
pulse-widths on GPIO channels using the class PWM.PulseGenerator.
"""
import RPIO.PWM as PWM

GPIO = 17
FREQ_HZ = 400

p = PWM.PulseGenerator()
p.set_frequency(GPIO, FREQ_HZ)

# The pulse-width default is 50%. You can set it to either '<n>%' or '<n>us':
p.set_frequency(GPIO, FREQ_HZ, pulse_width="10%")
p.set_frequency(GPIO, FREQ_HZ, pulse_width="20us")
