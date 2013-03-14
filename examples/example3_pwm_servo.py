"""
Demonstration of how to control servo pulses with RPIO.PWM
RPIO Documentation: http://pythonhosted.org/RPIO
"""
from RPIO import PWM

servo = PWM.Servo()

# Add servo pulse for GPIO 17 with 1200µs (1.2ms)
servo.set_servo(17, 1200)

# Add servo pulse for GPIO 17 with 2000µs (2.0ms)
servo.set_servo(17, 2000)

# Clear servo on GPIO17
servo.stop_servo(17)
