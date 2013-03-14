/*
 * This file is part of RPIO.
 *
 * Copyright
 *
 *     Copyright (C) 2013 Chris Hager <chris@linuxuser.at>
 *
 * License
 *
 *     This program is free software: you can redistribute it and/or modify
 *     it under the terms of the GNU Lesser General Public License as published
 *     by the Free Software Foundation, either version 3 of the License, or
 *     (at your option) any later version.
 *
 *     This program is distributed in the hope that it will be useful,
 *     but WITHOUT ANY WARRANTY; without even the implied warranty of
 *     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 *     GNU Lesser General Public License for more details at
 *     <http://www.gnu.org/licenses/lgpl-3.0-standalone.html>
 *
 * Documentation
 *
 *     http://pythonhosted.org/RPIO
 *
 * py_gpio.c is based on RPi.GPIO by Ben Croston, and provides a Python interface to
 * interact with the gpio-related C methods. 
 */
#include "Python.h"
#include "c_gpio.h"
#include "cpuinfo.h"

// All these will get exposed via the Python module
static PyObject *WrongDirectionException;
static PyObject *InvalidModeException;
static PyObject *InvalidDirectionException;
static PyObject *InvalidChannelException;
static PyObject *InvalidPullException;
static PyObject *ModeNotSetException;
static PyObject *high;
static PyObject *low;
static PyObject *input;
static PyObject *output;
static PyObject *alt0;
static PyObject *board;
static PyObject *bcm;
static PyObject *pud_off;
static PyObject *pud_up;
static PyObject *pud_down;
static PyObject *rpi_revision;
static PyObject *rpi_revision_hex;
static PyObject *version;

// Conversion from board_pin_id to gpio_id
// eg. gpio_id = *(*pin_to_gpio_rev2 + board_pin_id);
static const int pin_to_gpio_rev1[27] = {-1, -1, -1, 0, -1, 1, -1, 4, 14, -1, 15, 17, 18, 21, -1, 22, 23, -1, 24, 10, -1, 9, 25, 11, 8, -1, 7};
static const int pin_to_gpio_rev2[27] = {-1, -1, -1, 2, -1, 3, -1, 4, 14, -1, 15, 17, 18, 27, -1, 22, 23, -1, 24, 10, -1, 9, 25, 11, 8, -1, 7};
static const int (*pin_to_gpio)[27];

// Board header info is shifted left 8 bits (leaves space for up to 255 channel ids per header)
#define HEADER_P1 0<<8
#define HEADER_P5 5<<8
static const int gpio_to_pin_rev1[32] = {3, 5, -1, -1, 7, -1, -1, 26, 24, 21, 19, 23, -1, -1, 8, 10, -1, 11, 12, -1, -1, 13, 15, 16, 18, 22, -1, -1, -1, -1, -1, -1};
static const int gpio_to_pin_rev2[32] = {-1, -1, 3, 5, 7, -1, -1, 26, 24, 21, 19, 23, -1, -1, 8, 10, -1, 11, 12, -1, -1, -1, 15, 16, 18, 22, -1, 15, 3 | HEADER_P5, 4 | HEADER_P5, 5 | HEADER_P5, 6 | HEADER_P5};
static const int (*gpio_to_pin)[32];

// Flag whether to show warnings
static int gpio_warnings = 1;

// Which Raspberry Pi Revision is used (will be 1 or 2; 0 if not a Raspberry Pi).
// Source: /proc/cpuinfo (via cpuinfo.c)
static int revision_int = 0;
static char revision_hex[1024] = {'\0'};

// Internal map of directions (in/out) per gpio to prevent user mistakes.
static int gpio_direction[54];

// GPIO Modes
#define MODE_UNKNOWN -1
#define BOARD        10
#define BCM          11
static int gpio_mode = MODE_UNKNOWN;

// Read /proc/cpuinfo once and keep the info at hand for further requests
static void
cache_rpi_revision(void)
{
    revision_int = get_cpuinfo_revision(revision_hex);
}

// bcm_to_board() returns the pin for the supplied bcm_gpio_id or -1
// if not a valid gpio-id. P5 pins are returned with | HEADER_P5, so
// you can know the header with (retval >> 8) (either 0 or 5) and the
// exact pin number with (retval & 255).
static int
bcm_to_board(int bcm_gpio_id)
{
    return *(*gpio_to_pin+bcm_gpio_id);
}

// channel_to_bcm() returns the bcm gpio id for the supplied channel
// depending on current setmode. Only P1 header channels are supported.
// To use P5 you need to use BCM gpio ids (`setmode(BCM)`).
static int
board_to_bcm(int board_pin_id)
{
    return *(*pin_to_gpio+board_pin_id);
}

// module_setup is run on import of the GPIO module and calls the setup() method in c_gpio.c
static int
module_setup(void)
{
    int result;
    // printf("Setup module (mmap)\n");

    // Set all gpios to input in internal direction (not the system)
    int i=0;
    for (i=0; i<54; i++)
        gpio_direction[i] = -1;

    result = setup();
    if (result == SETUP_DEVMEM_FAIL) {
        PyErr_SetString(PyExc_RuntimeError, "No access to /dev/mem. Try running as root!");
        return SETUP_DEVMEM_FAIL;
    } else if (result == SETUP_MALLOC_FAIL) {
        PyErr_NoMemory();
        return SETUP_MALLOC_FAIL;
    } else if (result == SETUP_MMAP_FAIL) {
        PyErr_SetString(PyExc_RuntimeError, "Mmap failed on module import");
        return SETUP_MALLOC_FAIL;
    } else {
        // result == SETUP_OK
        return SETUP_OK;
    }
}

// Python function cleanup()
// Sets everything back to input
static PyObject*
py_cleanup(PyObject *self, PyObject *args)
{
    int i;
    for (i=0; i<54; i++) {
        if (gpio_direction[i] != -1) {
            // printf("GPIO %d --> INPUT\n", i);
            setup_gpio(i, INPUT, PUD_OFF);
            gpio_direction[i] = -1;
        }
    }

    Py_INCREF(Py_None);
    return Py_None;
}


// channel_to_gpio tries to convert the supplied channel-id to
// a BCM GPIO ID based on current setmode. On error it sets the
// Python error string and returns a value < 0.
static int
channel_to_gpio(int channel)
{
    int gpio;

     if (gpio_mode != BOARD && gpio_mode != BCM) {
        PyErr_SetString(ModeNotSetException, "Please set pin numbering mode using RPIO.setmode(RPIO.BOARD) or RPIO.setmode(RPIO.BCM)");
        return -1;
    }

   if ( (gpio_mode == BCM && (channel < 0 || channel > 31)) ||
        (gpio_mode == BOARD && (channel < 1 || channel > 26)) ) {
        PyErr_SetString(InvalidChannelException, "The channel sent is invalid on a Raspberry Pi (outside of range)");
        return -2;
    }

    if (gpio_mode == BOARD) {
        if ((gpio = board_to_bcm(channel)) == -1) {
            PyErr_SetString(InvalidChannelException, "The channel sent is invalid on a Raspberry Pi (not a valid pin)");
            return -3;
        }
    } else {
        // gpio_mode == BCM
        gpio = channel;
        if (bcm_to_board(gpio) == -1) {
            PyErr_SetString(InvalidChannelException, "The channel sent is invalid on a Raspberry Pi (not a valid gpio)");
            return -3;
        }
    }

    //printf("channel2bcm: %d -> %d", channel, gpio);
    return gpio;
}

static int
verify_input(int channel, int *gpio)
{
    if ((*gpio = channel_to_gpio(channel)) == -1)
        return 0;

    if ((gpio_direction[*gpio] != INPUT) && (gpio_direction[*gpio] != OUTPUT)) {
        PyErr_SetString(WrongDirectionException, "GPIO channel has not been set up");
        return 0;
    }

    return 1;
}

// python function setup(channel, direction, pull_up_down=PUD_OFF, initial=None)
static PyObject*
py_setup_channel(PyObject *self, PyObject *args, PyObject *kwargs)
{
    int gpio, channel, direction;
    int pud = PUD_OFF;
    int initial = -1;
    static char *kwlist[] = {"channel", "direction", "pull_up_down", "initial", NULL};
    int func;

    if (!PyArg_ParseTupleAndKeywords(args, kwargs, "ii|ii", kwlist, &channel, &direction, &pud, &initial))
        return NULL;

    if (direction != INPUT && direction != OUTPUT) {
        PyErr_SetString(InvalidDirectionException, "An invalid direction was passed to setup()");
        return NULL;
    }

    if (direction == OUTPUT)
        pud = PUD_OFF;

    if (pud != PUD_OFF && pud != PUD_DOWN && pud != PUD_UP) {
        PyErr_SetString(InvalidPullException, "Invalid value for pull_up_down - should be either PUD_OFF, PUD_UP or PUD_DOWN");
        return NULL;
    }

    if ((gpio = channel_to_gpio(channel)) < 0)
        return NULL;

    func = gpio_function(gpio);
    if (gpio_warnings &&                                      // warnings enabled and
         ((func != 0 && func != 1) ||                      // (already one of the alt functions or
         (gpio_direction[gpio] == -1 && func == 1)))  // already an output not set from this program)
    {
        PyErr_WarnEx(NULL, "This channel is already in use, continuing anyway.  Use RPIO.setwarnings(False) to disable warnings.", 1);
    }

//    printf("Setup GPIO %d direction %d pud %d\n", gpio, direction, pud);
    if (direction == OUTPUT && (initial == LOW || initial == HIGH)) {
//        printf("Writing intial value %d\n",initial);
        output_gpio(gpio, initial);
    }
    setup_gpio(gpio, direction, pud);
    gpio_direction[gpio] = direction;

    Py_INCREF(Py_None);
    return Py_None;
}

// python function output(channel, value)
static PyObject*
py_output_gpio(PyObject *self, PyObject *args)
{
    int gpio, channel, value;

    if (!PyArg_ParseTuple(args, "ii", &channel, &value))
        return NULL;

    if ((gpio = channel_to_gpio(channel)) < 0)
        return NULL;

    if (gpio_direction[gpio] != OUTPUT) {
        PyErr_SetString(WrongDirectionException, "The GPIO channel has not been set up as an OUTPUT");
        return NULL;
    }

//    printf("Output GPIO %d value %d\n", gpio, value);
    output_gpio(gpio, value);

    Py_INCREF(Py_None);
    return Py_None;
}


// python function output(channel, value) without direction check
static PyObject*
py_forceoutput_gpio(PyObject *self, PyObject *args)
{
    int gpio, channel, value;

    if (!PyArg_ParseTuple(args, "ii", &channel, &value))
        return NULL;

//    printf("Output GPIO %d value %d\n", gpio, value);
    if ((gpio = channel_to_gpio(channel)) < 0)
        return NULL;

    output_gpio(gpio, value);

    Py_INCREF(Py_None);
    return Py_None;
}

// python function output(channel, value) without direction check
static PyObject*
py_set_pullupdn(PyObject *self, PyObject *args, PyObject *kwargs)
{
    int gpio, channel;
    int pud = PUD_OFF;

    static char *kwlist[] = {"channel", "pull_up_down", NULL};
    if (!PyArg_ParseTupleAndKeywords(args, kwargs, "ii|ii", kwlist, &channel, &pud))
        return NULL;

    if ((gpio = channel_to_gpio(channel)) < 0)
        return NULL;

    // printf("Setting gpio %d PULLUPDN to %d", gpio, pud);
    set_pullupdn(gpio, pud);

    Py_INCREF(Py_None);
    return Py_None;
}

// python function value = input(channel)
static PyObject*
py_input_gpio(PyObject *self, PyObject *args)
{
    int gpio, channel;

    if (!PyArg_ParseTuple(args, "i", &channel))
        return NULL;

     if (!verify_input(channel, &gpio))
          return NULL;

    //    printf("Input GPIO %d\n", gpio);
    if (input_gpio(gpio))
        Py_RETURN_TRUE;
    else
        Py_RETURN_FALSE;
}

// python function value = input(channel) without direction check
static PyObject*
py_forceinput_gpio(PyObject *self, PyObject *args)
{
    int gpio, channel;

    if (!PyArg_ParseTuple(args, "i", &channel))
        return NULL;

    if ((gpio = channel_to_gpio(channel)) < 0)
        return NULL;

    //printf("Input GPIO %d\n", gpio);
    if (input_gpio(gpio))
        Py_RETURN_TRUE;
    else
        Py_RETURN_FALSE;
}

// python function setmode(mode)
static PyObject*
setmode(PyObject *self, PyObject *args)
{
    if (!PyArg_ParseTuple(args, "i", &gpio_mode))
        return NULL;

    if (gpio_mode != BOARD && gpio_mode != BCM)
    {
        PyErr_SetString(InvalidModeException, "An invalid mode was passed to setmode()");
        return NULL;
    }

    Py_INCREF(Py_None);
    return Py_None;
}

// python function value = gpio_function(gpio)
static PyObject*
py_gpio_function(PyObject *self, PyObject *args)
{
    int gpio, channel, f;
    PyObject *func;

    if (!PyArg_ParseTuple(args, "i", &channel))
        return NULL;

    if ((gpio = channel_to_gpio(channel)) < 0)
        return NULL;

    f = gpio_function(gpio);
    switch (f)
    {
        case 0 : f = INPUT;  break;
        case 1 : f = OUTPUT; break;
    }
    func = Py_BuildValue("i", f);
    return func;
}

// python function setwarnings(state)
static PyObject*
py_setwarnings(PyObject *self, PyObject *args)
{
    if (!PyArg_ParseTuple(args, "i", &gpio_warnings))
        return NULL;
    Py_INCREF(Py_None);
    return Py_None;
}

// channel2gpio binding
static PyObject*
py_channel_to_gpio(PyObject *self, PyObject *args)
{
    int channel, gpio;
    PyObject *func;

    if (!PyArg_ParseTuple(args, "i", &channel))
        return NULL;

    if ((gpio = channel_to_gpio(channel)) < 0)
        return NULL;

    func = Py_BuildValue("i", gpio);
    return func;
}

PyMethodDef rpi_gpio_methods[] = {
    {"setup", (PyCFunction)py_setup_channel, METH_VARARGS | METH_KEYWORDS, "Set up the GPIO channel, direction and (optional) pull/up down control\nchannel    - Either: RPi board pin number (not BCM GPIO 00..nn number).  Pins start from 1\n                or     : BCM GPIO number\ndirection - INPUT or OUTPUT\n[pull_up_down] - PUD_OFF (default), PUD_UP or PUD_DOWN\n[initial]        - Initial value for an output channel"},
    {"cleanup", py_cleanup, METH_VARARGS, "Clean up by resetting all GPIO channels that have been used by this program\nto INPUT with no pullup/pulldown and no event detection"},
    {"output", py_output_gpio, METH_VARARGS, "Output to a GPIO channel"},
    {"input", py_input_gpio, METH_VARARGS, "Input from a GPIO channel"},
    {"setmode", setmode, METH_VARARGS, "Set up numbering mode to use for channels.\nBOARD - Use Raspberry Pi board numbers\nBCM    - Use Broadcom GPIO 00..nn numbers"},
    {"setwarnings", py_setwarnings, METH_VARARGS, "Enable or disable warning messages"},

    // New methods in RPIO
    {"forceoutput", py_forceoutput_gpio, METH_VARARGS, "Force output to a GPIO channel, ignoring whether it has been set up before."},
    {"forceinput", py_forceinput_gpio, METH_VARARGS, "Force read input from a GPIO channel, ignoring whether it was set up before."},
    {"set_pullupdn", (PyCFunction)py_set_pullupdn, METH_VARARGS | METH_KEYWORDS, "Set pullup or -down resistor on a GPIO channel."},
    {"gpio_function", py_gpio_function, METH_VARARGS, "Return the current GPIO function (IN, OUT, ALT0)"},
    {"channel_to_gpio", py_channel_to_gpio, METH_VARARGS, "Return BCM or BOARD id of channel (depending on current setmode)"},
    {NULL, NULL, 0, NULL}
};

#if PY_MAJOR_VERSION > 2
static struct PyModuleDef rpigpiomodule = {
    PyModuleDef_HEAD_INIT,
    "_GPIO", /* name of module */
    NULL,         /* module documentation, may be NULL */
    -1,            /* size of per-interpreter state of the module,
                        or -1 if the module keeps state in global variables. */
    rpi_gpio_methods
};
#endif

#if PY_MAJOR_VERSION > 2
PyMODINIT_FUNC PyInit__GPIO(void)
#else
PyMODINIT_FUNC init_GPIO(void)
#endif
{
    PyObject *module = NULL;

#if PY_MAJOR_VERSION > 2
    if ((module = PyModule_Create(&rpigpiomodule)) == NULL)
        goto exit;
#else
    if ((module = Py_InitModule("_GPIO", rpi_gpio_methods)) == NULL)
        goto exit;
#endif

    WrongDirectionException = PyErr_NewException("RPIO.Exceptions.WrongDirectionException", NULL, NULL);
    PyModule_AddObject(module, "WrongDirectionException", WrongDirectionException);

    InvalidModeException = PyErr_NewException("RPIO.Exceptions.InvalidModeException", NULL, NULL);
    PyModule_AddObject(module, "InvalidModeException", InvalidModeException);

    InvalidDirectionException = PyErr_NewException("RPIO.Exceptions.InvalidDirectionException", NULL, NULL);
    PyModule_AddObject(module, "InvalidDirectionException", InvalidDirectionException);

    InvalidChannelException = PyErr_NewException("RPIO.Exceptions.InvalidChannelException", NULL, NULL);
    PyModule_AddObject(module, "InvalidChannelException", InvalidChannelException);

    InvalidPullException = PyErr_NewException("RPIO.Exceptions.InvalidPullException", NULL, NULL);
    PyModule_AddObject(module, "InvalidPullException", InvalidPullException);

    ModeNotSetException = PyErr_NewException("RPIO.Exceptions.ModeNotSetException", NULL, NULL);
    PyModule_AddObject(module, "ModeNotSetException", ModeNotSetException);

    high = Py_BuildValue("i", HIGH);
    PyModule_AddObject(module, "HIGH", high);

    low = Py_BuildValue("i", LOW);
    PyModule_AddObject(module, "LOW", low);

    output = Py_BuildValue("i", OUTPUT);
    PyModule_AddObject(module, "OUT", output);

    input = Py_BuildValue("i", INPUT);
    PyModule_AddObject(module, "IN", input);

    alt0 = Py_BuildValue("i", ALT0);
    PyModule_AddObject(module, "ALT0", alt0);

    board = Py_BuildValue("i", BOARD);
    PyModule_AddObject(module, "BOARD", board);

    bcm = Py_BuildValue("i", BCM);
    PyModule_AddObject(module, "BCM", bcm);

    pud_off = Py_BuildValue("i", PUD_OFF);
    PyModule_AddObject(module, "PUD_OFF", pud_off);

    pud_up = Py_BuildValue("i", PUD_UP);
    PyModule_AddObject(module, "PUD_UP", pud_up);

    pud_down = Py_BuildValue("i", PUD_DOWN);
    PyModule_AddObject(module, "PUD_DOWN", pud_down);

    // detect board revision and set up accordingly
    cache_rpi_revision();
    if (revision_int < 1)
    {
        PyErr_SetString(PyExc_SystemError, "This module can only be run on a Raspberry Pi!");
#if PY_MAJOR_VERSION > 2
        return NULL;
#else
        return;
#endif
    } else if (revision_int == 1) {
        pin_to_gpio = &pin_to_gpio_rev1;
        gpio_to_pin = &gpio_to_pin_rev1;
    } else {
        // assume revision 2
        pin_to_gpio = &pin_to_gpio_rev2;
        gpio_to_pin = &gpio_to_pin_rev2;
    }

    rpi_revision = Py_BuildValue("i", revision_int);
    PyModule_AddObject(module, "RPI_REVISION", rpi_revision);

    rpi_revision_hex = Py_BuildValue("s", revision_hex);
    PyModule_AddObject(module, "RPI_REVISION_HEX", rpi_revision_hex);

    version = Py_BuildValue("s", "0.10.0/0.4.2a");
    PyModule_AddObject(module, "VERSION_GPIO", version);

    // set up mmaped areas
    if (module_setup() != SETUP_OK ) {
#if PY_MAJOR_VERSION > 2
        return NULL;
#else
        return;
#endif
    }

    if (Py_AtExit(cleanup) != 0) {
      cleanup();
#if PY_MAJOR_VERSION > 2
        return NULL;
#else
        return;
#endif
    }

exit:
#if PY_MAJOR_VERSION > 2
    return module;
#else
    return;
#endif
}
