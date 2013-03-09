.. _ref-rpio-py:

``RPIO``, the Python module
==============================

RPIO.py extends `RPi.GPIO <http://pypi.python.org/pypi/RPi.GPIO>`_ in
various ways, and uses the BCM GPIO numbering scheme by default.

* :ref:`GPIO Interrupts <ref-rpio-py-interrupts>`
* :ref:`TCP Socket Interrupts <ref-rpio-py-tcpserver>`
* :ref:`GPIO Input & Output <ref-rpio-py-rpigpio>`
* :ref:`Hardware PWM <ref-rpio-pwm-py>`
* :ref:`more <ref-rpio-py-additions>`


GPIO & TCP Interrupts
---------------------

``RPIO`` can listen for two kinds of interrupts: ``GPIO`` and ``TCP``. GPIO interrupts happen
when the state on a specific GPIO input changes. TCP interrupts happen when a TCP client
connects to the built-in TCP server and sends a message.


.. _ref-rpio-py-interrupts:

GPIO Interrupts
^^^^^^^^^^^^^^^
Interrupts are used to receive notifications from the kernel when GPIO state
changes occur. Advantages include minimized cpu consumption, very fast
notification times, and the ability to trigger on specific edge transitions
(``rising``, ``falling`` or ``both``). You can also set a software pull-up 
or pull-down resistor.

.. method:: RPIO.add_interrupt_callback(gpio_id, callback, edge='both', pull_up_down=RPIO.PUD_OFF, threaded_callback=False)

   Adds a callback to receive notifications when a GPIO changes it's value. Possible ``pull_up_down`` values are 
   ``RPIO.PUD_UP``, ``RPIO.PUD_DOWN`` and ``RPIO.PUD_OFF`` (default). Possible edges are ``rising``,
   ``falling`` and ``both`` (default). Note that ``rising`` and ``falling`` edges may receive values
   not corresponding to the edge, so be sure to double check.


.. _ref-rpio-py-tcpserver:

TCP Socket Interrupts
^^^^^^^^^^^^^^^^^^^^^
Its easy to open ports for incoming TCP connections with just this one method:

.. method:: RPIO.add_tcp_callback(port, callback, threaded_callback=False)

   Adds a socket server callback, which will be started when a connected socket client sends something. This is implemented
   by RPIO creating a TCP server socket at the specified port. Incoming connections will be accepted when ``RPIO.wait_for_interrupts()`` runs.
   The callback must accept exactly two parameters: socket and message (eg. ``def callback(socket, msg)``).

   The callback can use the socket parameter to send values back to the client (eg. ``socket.send("hi there\n")``). To close the connection to a client, you can use ``socket.close()``. A client can close the connection the same way or by sending an empty message to the server.

You can test the TCP socket interrupts with ``$ telnet <your-ip> <your-port>`` (eg. ``$ telnet localhost 8080``). An empty string
tells the server to close the client connection (for instance if you just press enter in telnet, you'll get disconnected).


Example
^^^^^^^

The following example shows how to listen for GPIO and TCP interrupts (on port 8080)::

    import RPIO

    def gpio_callback(gpio_id, val):
        print("gpio %s: %s" % (gpio_id, val))

    def socket_callback(socket, val):
        print("socket %s: '%s'" % (socket.fileno(), val))
        socket.send("echo: %s\n" % val)

    # GPIO interrupt callbacks
    RPIO.add_interrupt_callback(7, gpio_callback)
    RPIO.add_interrupt_callback(9, gpio_callback, pull_up_down=RPIO.PUD_UP)

    # TCP socket server callback on port 8080
    RPIO.add_tcp_callback(8080, socket_callback)

    # Start the blocking epoll loop, and cleanup interfaces on exit
    try:
        RPIO.wait_for_interrupts()
    finally:
        RPIO.cleanup_interrupts()


If you want to receive a callback inside a Thread (to not block RPIO from returning to wait
for interrupts), set ``threaded_callback`` to ``True`` when adding it::


    # for GPIO interrupts
    RPIO.add_interrupt_callback(7, do_something, threaded_callback=True)

    # for socket interrupts
    RPIO.add_tcp_callback(8080, socket_callback, threaded_callback=True)

To stop the ``wait_for_interrupts()`` loop you can call ``RPIO.stop_waiting_for_interrupts()``.
After using ``RPIO.wait_for_interrupts()`` you should call ``RPIO.cleanup_interrupts()`` before your 
program quits, to shut everything down nicely.


.. _ref-rpio-py-rpigpio:

GPIO Input & Output
-------------------

RPIO extends `RPi.GPIO <http://pypi.python.org/pypi/RPi.GPIO>`_;
all the input and output handling works just the same:

::

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

You can use RPIO as a drop-in replacement for RPi.GPIO in your existing code like this:

::

    import RPIO as GPIO  # (if you've previously used `import RPi.GPIO as GPIO`)

To find out more about the methods and constants in RPIO you can run ``$ sudo pydoc RPIO``, or
use the help method inside Python::

    import RPIO
    help(RPIO)


Log Output
----------

To enable RPIO log output, import ``logging`` and set the loglevel to ``DEBUG`` before importing RPIO::

    import logging
    log_format = '%(levelname)s | %(asctime)-15s | %(message)s'
    logging.basicConfig(format=log_format, level=logging.DEBUG)
    import RPIO


.. _ref-rpio-py-additions:

Additions to RPi.GPIO
---------------------

Additional Constants

* ``RPIO.RPI_REVISION`` - the current board's revision (either ``1`` or ``2``)
* ``RPIO.RPI_REVISION_HEX`` - the cpu hex revision code (``0002`` .. ``000f``)

Additional Methods

* ``RPIO.gpio_function(gpio_id)`` - returns the current setup of a gpio (``IN, OUT, ALT0``)
* ``RPIO.set_pullupdn(gpio_id, pud)`` - set a pullup or -down resistor on a GPIO
* ``RPIO.forceinput(gpio_id)`` - reads the value of any gpio without needing to call setup() first
* ``RPIO.forceoutput(gpio_id, value)`` - writes a value to any gpio without needing to call setup() first 
  (**warning**: this can potentially harm your Raspberry)
* ``RPIO.sysinfo()`` - returns ``(hex_rev, model, revision, mb-ram and maker)`` of this Raspberry
* ``RPIO.version()`` - returns ``(version_rpio, version_cgpio)``

Interrupt Handling

* ``RPIO.add_interrupt_callback(gpio_id, callback, edge='both', pull_up_down=RPIO.PUD_OFF, threaded_callback=False)``
* ``RPIO.add_tcp_callback(port, callback, threaded_callback=False)``
* ``RPIO.del_interrupt_callback(gpio_id)``
* ``RPIO.wait_for_interrupts(epoll_timeout=1)``
* ``RPIO.stop_waiting_for_interrupts()``
*  implemented with ``epoll``
