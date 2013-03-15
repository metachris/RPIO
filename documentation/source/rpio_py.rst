.. _ref-rpio-py:

``RPIO``, the Python module
==============================

RPIO.py extends `RPi.GPIO <http://pypi.python.org/pypi/RPi.GPIO>`_ in
various ways, and uses the BCM GPIO numbering scheme by default.

* :ref:`GPIO Interrupts <ref-rpio-py-interrupts>` with debouncing
* :ref:`TCP Socket Interrupts <ref-rpio-py-tcpserver>`
* :ref:`GPIO Input & Output <ref-rpio-py-rpigpio>`
* :ref:`Hardware PWM <ref-rpio-pwm-py>`
* :ref:`more <ref-rpio-py-additions>`


GPIO & TCP Interrupts
---------------------

``RPIO`` can listen for two kinds of interrupts: ``GPIO`` and ``TCP``. GPIO interrupts happen
when the state on a specific GPIO input changes. TCP interrupts happen when a TCP socket client
sends a message.


.. method:: RPIO.wait_for_interrupts(threaded=False, epoll_timeout=1)

   This is the main blocking loop which, while active, will listen for interrupts and start
   your custom callbacks. At some point in your script you need to start this to receive interrupt
   callbacks. This blocking method is perfectly suited as "the endless loop that keeps your script
   running". 

   With the argument ``threaded=True``, this method starts in the background while your script
   continues in the main thread (RPIO will automatically shut down the thread when your script exits)::

       RPIO.wait_for_interrupts(threaded=True)


.. _ref-rpio-py-interrupts:

GPIO Interrupts
^^^^^^^^^^^^^^^
Interrupts are used to receive notifications from the kernel when GPIO state
changes occur. Advantages include minimized cpu consumption, very fast
notification times, and the ability to trigger on specific edge transitions
(``rising``, ``falling`` or ``both``). You can also set a software pull-up 
or pull-down resistor.

.. method:: RPIO.add_interrupt_callback(gpio_id, callback, edge='both', pull_up_down=RPIO.PUD_OFF, threaded_callback=False, debounce_timeout_ms=None)

   Adds a callback to receive notifications when a GPIO changes it's state from 0 to 1 or vice versa.

   * Possible edges are ``rising``, ``falling`` and ``both`` (default).
   * Possible ``pull_up_down`` values are ``RPIO.PUD_UP``, ``RPIO.PUD_DOWN`` and ``RPIO.PUD_OFF`` (default).  
   * If ``threaded_callback`` is ``True``, the callback will be started inside a thread. Else the callback will block RPIO from waiting for interrupts until it has finished (in the meantime no further callbacks are dispatched).
   * If ``debounce_timeout_ms`` is set, interrupt callbacks will not be started until the specified milliseconds have passed since the last interrupt. Adjust this to your needs (typically between 10ms and 1000ms.).

   The callback receives two arguments: the gpio number and the value (an integer, either ``0`` (Low) or ``1`` (High)). A callback typically looks like this::

    def gpio_callback(gpio_id, value):


.. method:: RPIO.del_interrupt_callback(gpio_id)

   Removes all callbacks for this particular GPIO.



.. _ref-rpio-py-tcpserver:

TCP Socket Interrupts
^^^^^^^^^^^^^^^^^^^^^
Its easy to open ports for incoming TCP connections with just this one method:

.. method:: RPIO.add_tcp_callback(port, callback, threaded_callback=False)

   Adds a socket server callback, which will be started when a connected socket client sends something. This is implemented
   by RPIO creating a TCP server socket at the specified port. Incoming connections will be accepted when ``RPIO.wait_for_interrupts()`` runs.
   The callback must accept exactly two parameters: socket and message (eg. ``def callback(socket, msg)``).

   The callback can use the socket parameter to send values back to the client (eg. ``socket.send("hi there\n")``). To close the connection to a client, use ``RPIO.close_tcp_client(..)``. A client can close the connection the same way or by sending an empty message to the server.

   You can use ``socket.getpeername()`` to get the IP address of the client. `Socket object documentation <http://docs.python.org/2/library/socket.html>`_.

You can test the TCP socket interrupts with ``$ telnet <your-ip> <your-port>`` (eg. ``$ telnet localhost 8080``). An empty string
tells the server to close the client connection (for instance if you just press enter in telnet, you'll get disconnected).


.. method:: RPIO.close_tcp_client(self, fileno)

   Closes the client socket connection and removes it from epoll. You can use this from the callback with ``RPIO.close_tcp_client(socket.fileno())``.


Example
^^^^^^^

The following example shows how to listen for some GPIO and TCP interrupts::

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

    # Blocking main epoll loop
    RPIO.wait_for_interrupts()


To receive a callback inside a Thread (and not block RPIO from returning to wait
for interrupts), set ``threaded_callback`` to ``True`` when adding it::

    # for GPIO interrupts
    RPIO.add_interrupt_callback(7, do_something, threaded_callback=True)

    # for socket interrupts
    RPIO.add_tcp_callback(8080, socket_callback, threaded_callback=True)


To debounce GPIO interrupts, you can add the argument ``debounce_timeout_ms``
to ``add_interrupt_callback(..)`` like this::

    RPIO.add_interrupt_callback(7, do_something, debounce_timeout_ms=100)


``wait_for_interrupts()`` listens for interrupts and dispatches the callbacks. 
You can add the argument ``threaded=True`` to have it run in a thread and your
script continue. Since v0.10.0, RPIO automatically shuts down everything nicely 
when your script quits.

::

    RPIO.wait_for_interrupts(threaded=True)


To stop ``wait_for_interrupts(..)``, call ``RPIO.stop_waiting_for_interrupts()``.


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

* ``RPIO.add_interrupt_callback(gpio_id, callback, edge='both', pull_up_down=RPIO.PUD_OFF, threaded_callback=False, debounce_timeout_ms=None)``
* ``RPIO.add_tcp_callback(port, callback, threaded_callback=False)``
* ``RPIO.del_interrupt_callback(gpio_id)``
* ``RPIO.close_tcp_client(fileno)``
* ``RPIO.wait_for_interrupts(threaded=False, epoll_timeout=1)``
* ``RPIO.stop_waiting_for_interrupts()``
*  implemented with ``epoll``
