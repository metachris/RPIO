"""
Examples of how to use RPIO as a drop-in replacement for RPi.GPIO
RPIO Documentation: http://pythonhosted.org/RPIO
"""
import RPIO

# set up input channel without pull-up
RPIO.setup(7, RPIO.IN)

# set up input channel with pull-up control. Can be
# PUD_UP, PUD_DOWN or PUD_OFF (default)
RPIO.setup(7, RPIO.IN, pull_up_down=RPIO.PUD_UP)

# read input from gpio 7
input_value = RPIO.input(7)

# set up GPIO output channel
RPIO.setup(8, RPIO.OUT)

# set gpio 8 to high
RPIO.output(8, True)

# set up output channel with an initial state
RPIO.setup(8, RPIO.OUT, initial=RPIO.LOW)

# change to BOARD numbering schema
RPIO.setmode(RPIO.BOARD)

# set software pullup on channel 17
RPIO.set_pullupdn(17, RPIO.PUD_UP)  # new in RPIO

# get the function of channel 8
RPIO.gpio_function(8)

# reset every channel that has been set up by this program,
# and unexport interrupt gpio interfaces
RPIO.cleanup()
