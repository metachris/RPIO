#!/usr/bin/env python
#
# This file is part of RPIO.
#
# Copyright
#
#     Copyright (C) 2013 Chris Hager <chris@linuxuser.at>
#
# License
#
#     This program is free software: you can redistribute it and/or modify
#     it under the terms of the GNU Lesser General Public License as published
#     by the Free Software Foundation, either version 3 of the License, or
#     (at your option) any later version.
#
#     This program is distributed in the hope that it will be useful,
#     but WITHOUT ANY WARRANTY; without even the implied warranty of
#     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#     GNU Lesser General Public License for more details at
#     <http://www.gnu.org/licenses/lgpl-3.0-standalone.html>
#
# Documentation
#
#     http://pythonhosted.org/RPIO
#
"""
This test suite runs on the Raspberry Pi and tests RPIO inside out.
"""
import sys
import time
import unittest
import logging
log_format = '%(levelname)s | %(asctime)-15s | %(message)s'
logging.basicConfig(format=log_format, level=logging.DEBUG)

from RPIO import PWM

GPIO_OUT = 17


class TestSequenceFunctions(unittest.TestCase):
    def test_servo(self):
        logging.info("= Testing Servo class on GPIO %s" % GPIO_OUT)
        #with self.assertRaises(RPIO.InvalidChannelException):
        #    RPIO.setup(5, RPIO.IN)
        #with self.assertRaises(RPIO.InvalidChannelException):
        #    RPIO.setup(0, RPIO.IN)
        #with self.assertRaises(RPIO.InvalidChannelException):
        #    RPIO.setup(32, RPIO.IN)

        servo = PWM.Servo()
        servo.set_servo(GPIO_OUT, 1200)
        time.sleep(3)
        servo.set_servo(GPIO_OUT, 1000)
        time.sleep(3)
        servo.set_servo(GPIO_OUT, 100)
        time.sleep(3)
        servo.stop_servo(GPIO_OUT)
        time.sleep(3)
        logging.info("done")


if __name__ == '__main__':
    logging.info("======================================")
    logging.info("= PWM Test Suite Run with Python %s   =" % \
            sys.version_info[0])
    logging.info("======================================")
    logging.info("")
    logging.info("")
    unittest.main()
