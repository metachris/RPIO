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
 */
int setup(int pw_incr_us, int hw);
void shutdown(void);
void set_loglevel(int level);

int init_channel(int channel, int subcycle_time_us);
int clear_channel(int channel);
int clear_channel_gpio(int channel, int gpio);
int print_channel(int channel);

int add_channel_pulse(int channel, int gpio, int width_start, int width);
char* get_error_message(void);
void set_softfatal(int enabled);

int is_setup(void);
int is_channel_initialized(int channel);
int get_pulse_incr_us(void);
int get_channel_subcycle_time_us(int channel);

#define DELAY_VIA_PWM   0
#define DELAY_VIA_PCM   1

#define LOG_LEVEL_DEBUG 0
#define LOG_LEVEL_ERRORS 1
#define LOG_LEVEL_DEFAULT LOG_LEVEL_DEBUG

// Default subcycle time
#define SUBCYCLE_TIME_US_DEFAULT 20000

// Subcycle minimum. We kept seeing no signals and strange behavior of the RPi
#define SUBCYCLE_TIME_US_MIN 3000

// Default pulse-width-increment-granularity
#define PULSE_WIDTH_INCREMENT_GRANULARITY_US_DEFAULT 10
