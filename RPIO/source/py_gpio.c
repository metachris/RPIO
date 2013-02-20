/*
Copyright (c) 2012-2013 Ben Croston

Permission is hereby granted, free of charge, to any person obtaining a copy of
this software and associated documentation files (the "Software"), to deal in
the Software without restriction, including without limitation the rights to
use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies
of the Software, and to permit persons to whom the Software is furnished to do
so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
*/

#include "Python.h"
#include "c_gpio.h"
#include "cpuinfo.h"

static PyObject *WrongDirectionException;
static PyObject *InvalidModeException;
static PyObject *InvalidDirectionException;
static PyObject *InvalidChannelException;
static PyObject *InvalidPullException;
static PyObject *ModeNotSetException;
static PyObject *SetupException;
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
static PyObject *version;

static int gpio_direction[54];
static const int pin_to_gpio_rev1[27] = {-1, -1, -1, 0, -1, 1, -1, 4, 14, -1, 15, 17, 18, 21, -1, 22, 23, -1, 24, 10, -1, 9, 25, 11, 8, -1, 7};
static const int pin_to_gpio_rev2[27] = {-1, -1, -1, 2, -1, 3, -1, 4, 14, -1, 15, 17, 18, 27, -1, 22, 23, -1, 24, 10, -1, 9, 25, 11, 8, -1, 7};
static const int (*pin_to_gpio)[27];
static int gpio_warnings = 1;

#define MODE_UNKNOWN -1
#define BOARD        10
#define BCM          11
static int gpio_mode = MODE_UNKNOWN;

// setup function run on import of the RPi.GPIO module
static int module_setup(void)
{
   int i, result;

//   printf("Setup module (mmap)\n");
   for (i=0; i<54; i++)
      gpio_direction[i] = -1;

   result = setup();
   if (result == SETUP_DEVMEM_FAIL)
   {
      PyErr_SetString(SetupException, "No access to /dev/mem.  Try running as root!");
      return SETUP_DEVMEM_FAIL;
   } else if (result == SETUP_MALLOC_FAIL) {
      PyErr_NoMemory();
      return SETUP_MALLOC_FAIL;
   } else if (result == SETUP_MMAP_FAIL) {
      PyErr_SetString(SetupException, "Mmap failed on module import");
      return SETUP_MALLOC_FAIL;
   } else { // result == SETUP_OK
      return SETUP_OK;
   }
}

// python function cleanup()
static PyObject *py_cleanup(PyObject *self, PyObject *args)
{
    int i;

    // clear event registers
    for (i=0; i<54; i++)
        if (gpio_direction[i] == INPUT)
	    {
//			printf("GPIO %d - clear events\n", i);
			set_rising_event(i, 0);
			set_falling_event(i, 0);
			set_high_event(i, 0);
			set_low_event(i, 0);
		}

    // set everything back to input
    for (i=0; i<54; i++)
        if (gpio_direction[i] != -1)
        {
//            printf("GPIO %d --> INPUT\n", i);
            setup_gpio(i, INPUT, PUD_OFF);
            gpio_direction[i] = -1;
        }
    
   Py_INCREF(Py_None);
   return Py_None;
}

static int verify_input(int channel, int *gpio)
{
    if (gpio_mode != BOARD && gpio_mode != BCM)
    {
        PyErr_SetString(ModeNotSetException, "Please set pin numbering mode using GPIO.setmode(GPIO.BOARD) or GPIO.setmode(GPIO.BCM)");
        return 0;
    }

    if ( (gpio_mode == BCM && (channel < 0 || channel > 53))
      || (gpio_mode == BOARD && (channel < 1 || channel > 26)) )
    {
        PyErr_SetString(InvalidChannelException, "The channel sent is invalid on a Raspberry Pi");
        return 0;
    }

    if (gpio_mode == BOARD)
    {
        *gpio = *(*pin_to_gpio+channel);
        if (*gpio == -1)
        {
            PyErr_SetString(InvalidChannelException, "The channel sent is invalid on a Raspberry Pi");
            return 0;
        }
    }
    else // gpio_mode == BCM
    {
        *gpio = channel;
    }

    if ((gpio_direction[*gpio] != INPUT) && (gpio_direction[*gpio] != OUTPUT))
    {
        PyErr_SetString(WrongDirectionException, "GPIO channel has not been set up");
        return 0;
    }
    return 1;
}

// python function setup(channel, direction, pull_up_down=PUD_OFF, initial=None)
static PyObject *py_setup_channel(PyObject *self, PyObject *args, PyObject *kwargs)
{
   int gpio, channel, direction;
   int pud = PUD_OFF;
   int initial = -1;
   static char *kwlist[] = {"channel", "direction", "pull_up_down", "initial", NULL};
   int func;
   
   if (!PyArg_ParseTupleAndKeywords(args, kwargs, "ii|ii", kwlist, &channel, &direction, &pud, &initial))
      return NULL;

   if (direction != INPUT && direction != OUTPUT)
   {
      PyErr_SetString(InvalidDirectionException, "An invalid direction was passed to setup()");
      return NULL;
   }

   if (direction == OUTPUT)
      pud = PUD_OFF;

   if (pud != PUD_OFF && pud != PUD_DOWN && pud != PUD_UP)
   {
      PyErr_SetString(InvalidPullException, "Invalid value for pull_up_down - should be either PUD_OFF, PUD_UP or PUD_DOWN");
      return NULL;
   }

   if (gpio_mode != BOARD && gpio_mode != BCM)
   {
      PyErr_SetString(ModeNotSetException, "Please set mode using GPIO.setmode(GPIO.BOARD) or GPIO.setmode(GPIO.BCM)");
      return NULL;
   }

   if ( (gpio_mode == BCM && (channel < 0 || channel > 53))
     || (gpio_mode == BOARD && (channel < 1 || channel > 26)) )
   {
      PyErr_SetString(InvalidChannelException, "The channel sent is invalid on a Raspberry Pi");
      return NULL;
   }

   if (gpio_mode == BOARD)
   {
      gpio = *(*pin_to_gpio+channel);
      if (gpio == -1)
      {
         PyErr_SetString(InvalidChannelException, "The channel sent is invalid on a Raspberry Pi");
         return NULL;
      }
   }
   else // gpio_mode == BCM
   {
      gpio = channel;
   }

   func = gpio_function(gpio);
   if (gpio_warnings &&                             // warnings enabled and
       ((func != 0 && func != 1) ||                 // (already one of the alt functions or
       (gpio_direction[gpio] == -1 && func == 1)))  // already an output not set from this program)
   {
      PyErr_WarnEx(NULL, "This channel is already in use, continuing anyway.  Use GPIO.setwarnings(False) to disable warnings.", 1);
   }
  
//   printf("Setup GPIO %d direction %d pud %d\n", gpio, direction, pud);
   set_rising_event(gpio, 0);
   set_falling_event(gpio, 0);
   set_high_event(gpio, 0);
   set_low_event(gpio, 0);
   if (direction == OUTPUT && (initial == LOW || initial == HIGH))
   {
//      printf("Writing intial value %d\n",initial);
      output_gpio(gpio, initial);
   }
   setup_gpio(gpio, direction, pud);
   gpio_direction[gpio] = direction;

   Py_INCREF(Py_None);
   return Py_None;
}

// python function output(channel, value)
static PyObject *py_output_gpio(PyObject *self, PyObject *args)
{
   int gpio, channel, value;

   if (!PyArg_ParseTuple(args, "ii", &channel, &value)) 
      return NULL;

   if (gpio_mode != BOARD && gpio_mode != BCM)
   {
      PyErr_SetString(ModeNotSetException, "Please set mode using GPIO.setmode(GPIO.BOARD) or GPIO.setmode(GPIO.BCM)");
      return NULL;
   }

   if ( (gpio_mode == BCM && (channel < 0 || channel > 53))
     || (gpio_mode == BOARD && (channel < 1 || channel > 26)) )
   {
      PyErr_SetString(InvalidChannelException, "The channel sent is invalid on a Raspberry Pi");
      return NULL;
   }

   if (gpio_mode == BOARD)
   {
      gpio = *(*pin_to_gpio+channel);
      if (gpio == -1)
      {
         PyErr_SetString(InvalidChannelException, "The channel sent is invalid on a Raspberry Pi");
         return NULL;
      }
   }
   else // gpio_mode == BCM
   {
      gpio = channel;
   }

   if (gpio_direction[gpio] != OUTPUT)
   {
      PyErr_SetString(WrongDirectionException, "The GPIO channel has not been set up as an OUTPUT");
      return NULL;
   }

//   printf("Output GPIO %d value %d\n", gpio, value);
   output_gpio(gpio, value);

   Py_INCREF(Py_None);
   return Py_None;
}

// python function value = input(channel)
static PyObject *py_input_gpio(PyObject *self, PyObject *args)
{
   int gpio, channel;

   if (!PyArg_ParseTuple(args, "i", &channel))
      return NULL;

    if (!verify_input(channel, &gpio))
        return NULL;
   
   //   printf("Input GPIO %d\n", gpio);
   if (input_gpio(gpio))
      Py_RETURN_TRUE;
   else
      Py_RETURN_FALSE;
}

// python function setmode(mode)
static PyObject *setmode(PyObject *self, PyObject *args)
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

// python function set_rising_event(channel, enable=True)
static PyObject *py_set_rising_event(PyObject *self, PyObject *args, PyObject *kwargs)
{
	int channel, gpio;
	int enable = 1;
    static char *kwlist[] = {"channel", "enable", NULL};
   
    if (!PyArg_ParseTupleAndKeywords(args, kwargs, "i|i", kwlist, &channel, &enable))
        return NULL;

    if (!verify_input(channel, &gpio))
        return NULL;
        
    set_rising_event(gpio, enable);
    
    Py_INCREF(Py_None);
    return Py_None;
}

// python function set_falling_event(channel, enable=True)
static PyObject *py_set_falling_event(PyObject *self, PyObject *args, PyObject *kwargs)
{
	int channel, gpio;
	int enable = 1;
    static char *kwlist[] = {"channel", "enable", NULL};
   
    if (!PyArg_ParseTupleAndKeywords(args, kwargs, "i|i", kwlist, &channel, &enable))
        return NULL;

    if (!verify_input(channel, &gpio))
        return NULL;

    set_falling_event(gpio, enable);
    
    Py_INCREF(Py_None);
    return Py_None;
}

// python function set_high_event(channel, enable=True)
static PyObject *py_set_high_event(PyObject *self, PyObject *args, PyObject *kwargs)
{
	int channel, gpio;
	int enable = 1;
    static char *kwlist[] = {"channel", "enable", NULL};
   
    if (!PyArg_ParseTupleAndKeywords(args, kwargs, "i|i", kwlist, &channel, &enable))
        return NULL;

    if (!verify_input(channel, &gpio))
        return NULL;

    set_high_event(gpio, enable);
    
    Py_INCREF(Py_None);
    return Py_None;
}

// python function set_low_event(channel, enable=True)
static PyObject *py_set_low_event(PyObject *self, PyObject *args, PyObject *kwargs)
{
	int channel, gpio;
	int enable = 1;
    static char *kwlist[] = {"channel", "enable", NULL};
   
    if (!PyArg_ParseTupleAndKeywords(args, kwargs, "i|i", kwlist, &channel, &enable))
        return NULL;

    if (!verify_input(channel, &gpio))
        return NULL;

    set_low_event(gpio, enable);
    
    Py_INCREF(Py_None);
    return Py_None;
}

// python function value = event_detected(channel)
static PyObject *py_event_detected(PyObject *self, PyObject *args)
{
   int gpio, channel;

   if (!PyArg_ParseTuple(args, "i", &channel))
      return NULL;

    if (!verify_input(channel, &gpio))
        return NULL;
   
   //   printf("Detect event GPIO %d\n", gpio);
   if (event_detected(gpio))
      Py_RETURN_TRUE;
   else
      Py_RETURN_FALSE;
}

// python function value = gpio_function(gpio)
static PyObject *py_gpio_function(PyObject *self, PyObject *args)
{
   int gpio, f;
   PyObject *func;
   
   if (!PyArg_ParseTuple(args, "i", &gpio))
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
static PyObject *py_setwarnings(PyObject *self, PyObject *args)
{
   if (!PyArg_ParseTuple(args, "i", &gpio_warnings))
      return NULL;
   Py_INCREF(Py_None);
   return Py_None;
}

PyMethodDef rpi_gpio_methods[] = {
   {"setup", (PyCFunction)py_setup_channel, METH_VARARGS | METH_KEYWORDS, "Set up the GPIO channel, direction and (optional) pull/up down control\nchannel   - Either: RPi board pin number (not BCM GPIO 00..nn number).  Pins start from 1\n            or    : BCM GPIO number\ndirection - INPUT or OUTPUT\n[pull_up_down] - PUD_OFF (default), PUD_UP or PUD_DOWN\n[initial]      - Initial value for an output channel"},
   {"cleanup", py_cleanup, METH_VARARGS, "Clean up by resetting all GPIO channels that have been used by this program to INPUT with no pullup/pulldown and no event detection"},
   {"output", py_output_gpio, METH_VARARGS, "Output to a GPIO channel"},
   {"input", py_input_gpio, METH_VARARGS, "Input from a GPIO channel"},
   {"setmode", setmode, METH_VARARGS, "Set up numbering mode to use for channels.\nBOARD - Use Raspberry Pi board numbers\nBCM   - Use Broadcom GPIO 00..nn numbers"},
   {"set_rising_event", (PyCFunction)py_set_rising_event, METH_VARARGS | METH_KEYWORDS, "EXPERIMENTAL.  Set rising edge detection\nchannel   - Either: RPi board pin number (not BCM GPIO 00..nn number).  Pins start from 1\n            or    : BCM GPIO number\n[enable] - True (default) or False"},
   {"set_falling_event", (PyCFunction)py_set_falling_event, METH_VARARGS | METH_KEYWORDS, "EXPERIMENTAL.  Set falling edge detection\nchannel   - Either: RPi board pin number (not BCM GPIO 00..nn number).  Pins start from 1\n            or    : BCM GPIO number\n[enable] - True (default) or False"},
   {"set_high_event", (PyCFunction)py_set_high_event, METH_VARARGS | METH_KEYWORDS, "EXPERIMENTAL.  Set high detection\nchannel   - Either: RPi board pin number (not BCM GPIO 00..nn number).  Pins start from 1\n            or    : BCM GPIO number\n[enable] - True (default) or False"},
   {"set_low_event", (PyCFunction)py_set_low_event, METH_VARARGS | METH_KEYWORDS, "EXPERIMENTAL.  Set low detection\nchannel   - Either: RPi board pin number (not BCM GPIO 00..nn number).  Pins start from 1\n            or    : BCM GPIO number\n[enable] - True (default) or False"},
   {"event_detected", py_event_detected, METH_VARARGS, "EXPERIMENTAL.  Returns True if an event has occured"},
   {"gpio_function", py_gpio_function, METH_VARARGS, "Return the current GPIO function (IN, OUT, ALT0)"},
   {"setwarnings", py_setwarnings, METH_VARARGS, "Enable or disable warning messages"},
   {NULL, NULL, 0, NULL}
};

#if PY_MAJOR_VERSION > 2
static struct PyModuleDef rpigpiomodule = {
   PyModuleDef_HEAD_INIT,
   "RPi.GPIO", /* name of module */
   NULL,       /* module documentation, may be NULL */
   -1,         /* size of per-interpreter state of the module,
                  or -1 if the module keeps state in global variables. */
   rpi_gpio_methods
};
#endif

#if PY_MAJOR_VERSION > 2
PyMODINIT_FUNC PyInit_GPIO(void)
#else
PyMODINIT_FUNC initGPIO(void)
#endif
{
   PyObject *module = NULL;
   int revision = -1;

#if PY_MAJOR_VERSION > 2
   if ((module = PyModule_Create(&rpigpiomodule)) == NULL)
      goto exit;
#else
   if ((module = Py_InitModule("RPi.GPIO", rpi_gpio_methods)) == NULL)
      goto exit;
#endif

   WrongDirectionException = PyErr_NewException("RPi.GPIO.WrongDirectionException", NULL, NULL);
   PyModule_AddObject(module, "WrongDirectionException", WrongDirectionException);

   InvalidModeException = PyErr_NewException("RPi.GPIO.InvalidModeException", NULL, NULL);
   PyModule_AddObject(module, "InvalidModeException", InvalidModeException);

   InvalidDirectionException = PyErr_NewException("RPi.GPIO.InvalidDirectionException", NULL, NULL);
   PyModule_AddObject(module, "InvalidDirectionException", InvalidDirectionException);

   InvalidChannelException = PyErr_NewException("RPi.GPIO.InvalidChannelException", NULL, NULL);
   PyModule_AddObject(module, "InvalidChannelException", InvalidChannelException);

   InvalidPullException = PyErr_NewException("RPi.GPIO.InvalidPullException", NULL, NULL);
   PyModule_AddObject(module, "InvalidPullException", InvalidPullException);

   ModeNotSetException = PyErr_NewException("RPi.GPIO.ModeNotSetException", NULL, NULL);
   PyModule_AddObject(module, "ModeNotSetException", ModeNotSetException);

   SetupException = PyErr_NewException("RPi.GPIO.SetupException", NULL, NULL);
   PyModule_AddObject(module, "SetupException", SetupException);

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
   revision = get_rpi_revision();
   if (revision == -1)
   {
      PyErr_SetString(SetupException, "This module can only be run on a Raspberry Pi!");
#if PY_MAJOR_VERSION > 2
      return NULL;
#else
      return;
#endif
   } else if (revision == 1) {
      pin_to_gpio = &pin_to_gpio_rev1;
   } else { // assume revision 2
      pin_to_gpio = &pin_to_gpio_rev2;
   }
   rpi_revision = Py_BuildValue("i", revision);
   PyModule_AddObject(module, "RPI_REVISION", rpi_revision);

   version = Py_BuildValue("s", "0.4.2a");
   PyModule_AddObject(module, "VERSION", version);

   // set up mmaped areas
   if (module_setup() != SETUP_OK )
   {
#if PY_MAJOR_VERSION > 2
      return NULL;
#else
      return;
#endif
   }
      
   if (Py_AtExit(cleanup) != 0)
   {
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
