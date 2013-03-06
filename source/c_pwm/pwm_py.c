/*
 * This file is part of RPIO.
 *
 * License: GPLv3+
 * Author: Chris Hager <chris@linuxuser.at>
 * URL: https://github.com/metachris/RPIO
 */
#include "Python.h"
#include <stdlib.h>
#include "pwm.h"

static void *
raise_error(void)
{
    PyErr_SetString(PyExc_RuntimeError, get_error_message());
    return NULL;
}

// python function int setup(int pw_incr_us, int hw)
static PyObject*
py_setup(PyObject *self, PyObject *args)
{
    int delay_hw=-1, pw_incr_us=-1;

    if (!PyArg_ParseTuple(args, "|ii", &pw_incr_us, &delay_hw))
        return NULL;

    if (pw_incr_us == -1)
        pw_incr_us = PULSE_WIDTH_INCREMENT_GRANULARITY_US_DEFAULT;
    if (delay_hw == -1)
        delay_hw = DELAY_VIA_PWM;

    if (setup(pw_incr_us, delay_hw) == EXIT_FAILURE)
        return raise_error();

    Py_INCREF(Py_None);
    return Py_None;
}

// python function cleanup()
static PyObject*
py_cleanup(PyObject *self, PyObject *args)
{
    shutdown();

    Py_INCREF(Py_None);
    return Py_None;
}

// python function init_channel(int channel, int subcycle_time_us)
static PyObject*
py_init_channel(PyObject *self, PyObject *args)
{
    int channel, subcycle_time_us=-1;

    if (!PyArg_ParseTuple(args, "i|i", &channel, &subcycle_time_us))
        return NULL;

    if (subcycle_time_us == -1)
        subcycle_time_us = SUBCYCLE_TIME_US_DEFAULT;

    if (init_channel(channel, subcycle_time_us) == EXIT_FAILURE)
        return raise_error();

    Py_INCREF(Py_None);
    return Py_None;
}

// python function clear_channel_pulses(int channel)
static PyObject*
py_clear_channel_pulses(PyObject *self, PyObject *args)
{
    int channel;

    if (!PyArg_ParseTuple(args, "i", &channel))
        return NULL;

    if (clear_channel_pulses(channel) == EXIT_FAILURE)
        return raise_error();

    Py_INCREF(Py_None);
    return Py_None;
}

// python function (void) add_channel_pulse(int channel, int gpio, int width_start, int width)
static PyObject*
py_add_channel_pulse(PyObject *self, PyObject *args)
{
    int channel, gpio, width_start, width;

    if (!PyArg_ParseTuple(args, "iiii", &channel, &gpio, &width_start, &width))
        return NULL;

    if (add_channel_pulse(channel, gpio, width_start, width) == EXIT_FAILURE)
        return raise_error();

    Py_INCREF(Py_None);
    return Py_None;
}

// python function print_channel(int channel)
static PyObject*
py_print_channel(PyObject *self, PyObject *args)
{
    int channel;

    if (!PyArg_ParseTuple(args, "i", &channel))
        return NULL;

    if (print_channel(channel) == EXIT_FAILURE)
        return raise_error();

    Py_INCREF(Py_None);
    return Py_None;
}

// python function (void) set_loglevel(level);
static PyObject*
py_set_loglevel(PyObject *self, PyObject *args)
{
    int level;

    if (!PyArg_ParseTuple(args, "i", &level))
        return NULL;

    set_loglevel(level);

    Py_INCREF(Py_None);
    return Py_None;
}

static PyMethodDef pwm_methods[] = {
    {"setup", py_setup, METH_VARARGS, "Setup the DMA-PWM system"},
    {"cleanup", py_cleanup, METH_VARARGS, "Stop all pwms and clean up DMA engine"},
    {"init_channel", py_init_channel, METH_VARARGS, "Setup a channel with a specific period time and hardware"},
    {"clear_channel_pulses", py_clear_channel_pulses, METH_VARARGS, "Clear all pulses on this channel"},
    {"add_channel_pulse", py_add_channel_pulse, METH_VARARGS, "Add a specific pulse to a channel"},
    {"print_channel", py_print_channel, METH_VARARGS, "Print info about a specific channel"},
    {"set_loglevel", py_set_loglevel, METH_VARARGS, "Set the loglevel to either 0 (debug) or 1 (errors)"},
    {NULL, NULL, 0, NULL}
};




#if PY_MAJOR_VERSION > 2
static struct PyModuleDef pwmmodule = {
    PyModuleDef_HEAD_INIT,
    "_PWM", /* name of module */
    NULL,         /* module documentation, may be NULL */
    -1,            /* size of per-interpreter state of the module,
                        or -1 if the module keeps state in global variables. */
    pwm_methods
};
#endif

#if PY_MAJOR_VERSION > 2
PyMODINIT_FUNC PyInit__PWM(void)
#else
PyMODINIT_FUNC init_PWM(void)
#endif
{
    PyObject *module = NULL;

#if PY_MAJOR_VERSION > 2
    if ((module = PyModule_Create(&pwmmodule)) == NULL)
        return module;
#else
    if ((module = Py_InitModule("_PWM", pwm_methods)) == NULL)
        return;
#endif

    PyModule_AddObject(module, "VERSION", Py_BuildValue("s", "0.1.1"));
    PyModule_AddObject(module, "DELAY_VIA_PWM", Py_BuildValue("i", DELAY_VIA_PWM));
    PyModule_AddObject(module, "DELAY_VIA_PCM", Py_BuildValue("i", DELAY_VIA_PCM));
    PyModule_AddObject(module, "LOG_LEVEL_DEBUG", Py_BuildValue("i", LOG_LEVEL_DEBUG));
    PyModule_AddObject(module, "LOG_LEVEL_ERRORS", Py_BuildValue("i", LOG_LEVEL_ERRORS));
    PyModule_AddObject(module, "LOG_LEVEL_DEFAULT", Py_BuildValue("i", LOG_LEVEL_DEFAULT));
    PyModule_AddObject(module, "SUBCYCLE_TIME_US_DEFAULT", Py_BuildValue("i", SUBCYCLE_TIME_US_DEFAULT));
    PyModule_AddObject(module, "PULSE_WIDTH_INCREMENT_GRANULARITY_US_DEFAULT", Py_BuildValue("i", PULSE_WIDTH_INCREMENT_GRANULARITY_US_DEFAULT));

    // Enable PWM.C soft-fatal mode in order to convert them to python exceptions
    set_softfatal(1);

    // Add shutdown handler to be executed when python script stops
    if (Py_AtExit(shutdown) != 0) {
      shutdown();
    }

#if PY_MAJOR_VERSION > 2
    return module;
#else
    return;
#endif
}
