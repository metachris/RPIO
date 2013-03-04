/*
*/
#include "Python.h"
#include "pwm.h"

static PyObject *version;

// python function setup(int delay_hw=DELAY_PWM, int pw_incr_us)
static PyObject*
py_setup(PyObject *self, PyObject *args)
{
    int delay_hw=-1, pw_incr_us=-1;

    if (!PyArg_ParseTuple(args, "|ii", &delay_hw, &pw_incr_us))
        return NULL;

    if (delay_hw == -1)
        delay_hw = DELAY_VIA_PWM;
    if (pw_incr_us == -1)
        pw_incr_us = pulse_width_incr_us;

    setup(delay_hw, pw_incr_us);

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

// python function init_channel(int channel, int gpio, int period_time_us)
static PyObject*
py_init_channel(PyObject *self, PyObject *args)
{
    int channel, gpio, period_time_us;

    if (!PyArg_ParseTuple(args, "iii", &channel, &gpio, &period_time_us))
        return NULL;

    init_channel(channel, gpio, period_time_us);

    Py_INCREF(Py_None);
    return Py_None;
}

// python function set_channel_pulse(int channel, int width);
static PyObject*
py_set_channel_pulse(PyObject *self, PyObject *args)
{
    int channel, width;

    if (!PyArg_ParseTuple(args, "ii", &channel, &width))
        return NULL;

    set_channel_pulse(channel, width);

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

    print_channel(channel);

    Py_INCREF(Py_None);
    return Py_None;
}


static PyMethodDef pwm_methods[] = {
    {"setup", (PyCFunction)py_setup, METH_VARARGS, "Setup the DMA-PWM system"},
    {"cleanup", py_cleanup, METH_VARARGS, "Stop all pwms and clean up DMA engine"},
    {"init_channel", (PyCFunction)py_init_channel, METH_VARARGS, "Setup a channel with a specific period time and hardware"},
    {"set_channel_pulse", py_set_channel_pulse, METH_VARARGS, "Set a specific pulse width for a channel"},
    {"print_channel", py_print_channel, METH_VARARGS, "Print info about a specific channel"},
    {NULL, NULL, 0, NULL}
};




#if PY_MAJOR_VERSION > 2
static struct PyModuleDef pwmmodule = {
    PyModuleDef_HEAD_INIT,
    "PWM", /* name of module */
    NULL,         /* module documentation, may be NULL */
    -1,            /* size of per-interpreter state of the module,
                        or -1 if the module keeps state in global variables. */
    pwm_methods
};
#endif

#if PY_MAJOR_VERSION > 2
PyMODINIT_FUNC PyInit_CPWM(void)
#else
PyMODINIT_FUNC initCPWM(void)
#endif
{
    PyObject *module = NULL;

#if PY_MAJOR_VERSION > 2
    if ((module = PyModule_Create(&pwmmodule)) == NULL)
        return module;
#else
    if ((module = Py_InitModule("CPWM", pwm_methods)) == NULL)
        return;
#endif

    version = Py_BuildValue("s", "0.10");
    PyModule_AddObject(module, "VERSION_CPWM", version);

    if (Py_AtExit(shutdown) != 0) {
      shutdown();
#if PY_MAJOR_VERSION > 2
        return NULL;
#else
        return;
#endif
    }

#if PY_MAJOR_VERSION > 2
    return module;
#else
    return;
#endif
}
