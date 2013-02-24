#!/usr/bin/env python
"""
This test suite runs on the Raspberry Pi and tests RPIO inside out.
"""
import os
import time
import unittest
import logging
log_format = '%(levelname)s | %(asctime)-15s | %(message)s'
logging.basicConfig(format=log_format, level=logging.DEBUG)

import RPIO

GPIO_IN = 14
GPIO_OUT = 17


class TestSequenceFunctions(unittest.TestCase):
    def setUp(self):
        RPIO.setwarnings(False)

    def test1_version(self):
        logging.info("Version: %s (%s)", RPIO.VERSION, RPIO.VERSION_GPIO)

    def test2_rpio_cmd(self):
        logging.info("Running `sudo rpio --version`...")
        #os.system("sudo python rpio --version")
        logging.info("Running `sudo rpio -I`...")
        #os.system("sudo python rpio -I")
        logging.info("Running `sudo rpio -i 5,%s,%s`...", GPIO_IN, GPIO_OUT)
        #os.system("sudo python rpio -i 5,%s,%s" % (GPIO_IN, GPIO_OUT)

    def test3_input(self):
        with self.assertRaises(RPIO.InvalidChannelException):
            # 5 is not a valid gpio
            RPIO.setup(5, RPIO.IN)
        with self.assertRaises(RPIO.InvalidChannelException):
            # 5 is not a valid gpio
            RPIO.setup(0, RPIO.IN)
        with self.assertRaises(RPIO.InvalidChannelException):
            # 5 is not a valid gpio
            RPIO.setup(32, RPIO.IN)

        RPIO.setup(GPIO_IN, RPIO.IN)
        logging.info("Input from GPIO-%s w/ PULLOFF:  %s", \
                GPIO_IN, RPIO.input(GPIO_IN))
        RPIO.set_pullupdn(GPIO_IN, RPIO.PUD_UP)
        logging.info("Input from GPIO-%s w/ PULLUP:   %s", \
                GPIO_IN, RPIO.input(GPIO_IN))
        RPIO.set_pullupdn(GPIO_IN, RPIO.PUD_DOWN)
        logging.info("Input from GPIO-%s w/ PULLDOWN: %s", \
                GPIO_IN, RPIO.input(GPIO_IN))
        RPIO.set_pullupdn(GPIO_IN, RPIO.PUD_OFF)

    def test4_output(self):
        with self.assertRaises(RPIO.InvalidChannelException):
            # 5 is not a valid gpio
            RPIO.setup(5, RPIO.OUT)
        with self.assertRaises(RPIO.InvalidChannelException):
            # 5 is not a valid gpio
            RPIO.setup(0, RPIO.OUT)
        with self.assertRaises(RPIO.InvalidChannelException):
            # 5 is not a valid gpio
            RPIO.setup(32, RPIO.OUT)

        logging.info("Setting up GPIO-%s as output...", GPIO_OUT)
        RPIO.setup(GPIO_OUT, RPIO.OUT)
        logging.info("Setting GPIO-%s output to 1...", GPIO_OUT)
        RPIO.output(GPIO_OUT, RPIO.HIGH)
        time.sleep(3)
        logging.info("Setting GPIO-%s output to 0...", GPIO_OUT)
        RPIO.output(GPIO_OUT, RPIO.LOW)

    def test5_board_pin_numbers(self):
        pass

    def test6_interrupts(self):
        pass


if __name__ == '__main__':
    unittest.main()
