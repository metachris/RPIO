#!/usr/bin/env python
"""
This test suite runs on the Raspberry Pi and tests RPIO inside out.
"""
import os
import sys
import time
import unittest
import socket
from threading import Thread
import logging
log_format = '%(levelname)s | %(asctime)-15s | %(message)s'
logging.basicConfig(format=log_format, level=logging.DEBUG)

import RPIO
RPIO.setwarnings(False)

GPIO_IN = 17
GPIO_OUT = 14


def run(cmd):
        logging.info("Running `%s`...", cmd)
        os.system(cmd)


class TestSequenceFunctions(unittest.TestCase):
    def test1_version(self):
        logging.info("Version: %s (%s)", RPIO.VERSION, RPIO.VERSION_GPIO)

    def test2_rpio_cmd(self):
        logging.info(" ")
        cmd = "sudo python rpio" if sys.version_info[0] == 2 else \
              "sudo python3 rpio"
        logging.info("=== rpio COMMAND LINE TOOL TESTS (`%s`)===", cmd)
        run("%s --version" % cmd)
        run("%s -v -I" % cmd)
        run("%s -v -i 5,%s,%s" % (cmd, GPIO_IN, GPIO_OUT))
        # run("sudo python rpio --update-man")
        run("%s --sysinfo" % cmd)

    def test3_input(self):
        logging.info(" ")
        logging.info(" ")
        logging.info("=== INPUT TESTS ===")
        with self.assertRaises(RPIO.InvalidChannelException):
            RPIO.setup(5, RPIO.IN)
        with self.assertRaises(RPIO.InvalidChannelException):
            RPIO.setup(0, RPIO.IN)
        with self.assertRaises(RPIO.InvalidChannelException):
            RPIO.setup(32, RPIO.IN)

        RPIO.setup(GPIO_IN, RPIO.IN)
        logging.info(" ")
        logging.info("--------------------------------------")
        logging.info("Input from GPIO-%s w/ PULLOFF:  %s", \
                GPIO_IN, RPIO.input(GPIO_IN))
        RPIO.set_pullupdn(GPIO_IN, RPIO.PUD_UP)
        logging.info("Input from GPIO-%s w/ PULLUP:   %s", \
                GPIO_IN, RPIO.input(GPIO_IN))
        RPIO.set_pullupdn(GPIO_IN, RPIO.PUD_DOWN)
        logging.info("Input from GPIO-%s w/ PULLDOWN: %s", \
                GPIO_IN, RPIO.input(GPIO_IN))
        logging.info("--------------------------------------")
        logging.info(" ")
        RPIO.set_pullupdn(GPIO_IN, RPIO.PUD_OFF)

    def test4_output(self):
        logging.info(" ")
        logging.info(" ")
        logging.info("=== OUTPUT TESTS ===")
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
        RPIO.setup(GPIO_OUT, RPIO.OUT, initial=RPIO.LOW)
        RPIO.setup(GPIO_OUT, RPIO.OUT)
        logging.info("Setting GPIO-%s output to 1...", GPIO_OUT)
        RPIO.output(GPIO_OUT, RPIO.HIGH)
        time.sleep(2)
        logging.info("Setting GPIO-%s output to 0...", GPIO_OUT)
        RPIO.output(GPIO_OUT, RPIO.LOW)

    def test5_board_pin_numbers(self):
        logging.info(" ")
        logging.info(" ")
        logging.info("=== BCM AND BOARD NUMBERING TESTS ===")

        RPIO.setmode(RPIO.BCM)
        pins = RPIO.GPIO_LIST_R1 if RPIO.RPI_REVISION == 1 \
                else RPIO.GPIO_LIST_R2
        logging.info("testing bcm gpio numbering: %s", pins)
        for pin in pins:
            gpio_id = RPIO.channel_to_gpio(pin)
            logging.info("- BCM channel %s = gpio %s", pin, gpio_id)
        with self.assertRaises(RPIO.InvalidChannelException):
            gpio_id = RPIO.channel_to_gpio(32)
        with self.assertRaises(RPIO.InvalidChannelException):
            gpio_id = RPIO.channel_to_gpio(5)

        logging.info(" ")

        pins = RPIO.PIN_LIST
        RPIO.setmode(RPIO.BOARD)
        logging.info("testing board gpio numbering: %s", pins)
        for pin in pins:
            if pin >> 8 > 0:
                # py_gpio.c cannot deal with BOARD->BCM of P5 pins yet
                continue
            gpio_id = RPIO.channel_to_gpio(pin)
            logging.info("- BOARD channel %s = gpio %s", pin, gpio_id)
        with self.assertRaises(RPIO.InvalidChannelException):
            gpio_id = RPIO.channel_to_gpio(0)

        RPIO.setmode(RPIO.BCM)

    def test6_interrupts(self):
        logging.info(" ")
        logging.info(" ")
        logging.info("=== INTERRUPT TESTS (3x 5sec) ==")

        def test_callback(*args):
            logging.info("- interrupt callback received: %s", (args))

        def stop_interrupts(timeout=3):
            time.sleep(timeout)
            RPIO.stop_waiting_for_interrupts()
            logging.info("- called `stop_waiting_for_interrupts()`")

        PORT = 8080

        def socket_callback(socket, msg):
            logging.info("Socket msg received: %s", msg)

        def socket_client():
            logging.info("Socket client connecting in 3 seconds...")
            time.sleep(3)
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect(("localhost", PORT))
            s.sendall("Hello, world".encode('utf-8'))
            s.close()
            logging.info("Socket client done...")

        #
        # Interrupt test with socket comm
        #
        logging.info(" ")
        logging.info("Testing interrupts on GPIO-%s and socket comm", GPIO_IN)
        RPIO.add_tcp_callback(PORT, socket_callback)
        RPIO.add_interrupt_callback(GPIO_IN, test_callback, edge='both', \
                pull_up_down=RPIO.PUD_DOWN)

        logging.info("- waiting 10s for interrupts on GPIO-%s...", GPIO_IN)
        Thread(target=socket_client).start()
        Thread(target=stop_interrupts, args=(10,)).start()

        RPIO.wait_for_interrupts()

        logging.info("-")
        RPIO.cleanup()

        #
        # Auto interrupt shutdown with thread and stop_waiting_for_interrupts
        #
        logging.info(" ")
        RPIO.add_interrupt_callback(GPIO_IN, test_callback, edge='both', \
                pull_up_down=RPIO.PUD_OFF)
        RPIO.add_interrupt_callback(GPIO_OUT, test_callback, edge='falling', \
                pull_up_down=RPIO.PUD_UP)
        logging.info("- waiting 5s for interrupts on gpio %s and %s...", \
                GPIO_IN, GPIO_OUT)
        Thread(target=stop_interrupts, args=(5,)).start()
        RPIO.wait_for_interrupts()
        logging.info("-")
        RPIO.cleanup()

        logging.info("ALL DONE :)")


if __name__ == '__main__':
    logging.info("==================================")
    logging.info("= Test Suite Run with Python %s   =" % \
            sys.version_info[0])
    logging.info("==================================")
    logging.info("")
    logging.info("")
    unittest.main()
