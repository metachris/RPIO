/*
 * This file is part of RPIO.
 *
 * License: GPLv3+
 * Author: Chris Hager <chris@linuxuser.at>
 * URL: https://github.com/metachris/RPIO
 */
void setup(int pw_incr_us, int hw);
void shutdown(void);
void set_loglevel(uint8_t level);

void init_channel(int channel, int period_time_us);
void clear_channel_pulses(int channel);
void print_channel(int channel);

void add_channel_pulse(int channel, int gpio, int width_start, int width);

#define DELAY_VIA_PWM   0
#define DELAY_VIA_PCM   1

#define LOG_LEVEL_DEBUG 0
#define LOG_LEVEL_ERRORS 1

// Full period time in microseconds. Defaults to 10ms within
// which you can add pulses. Cannot be lower than 2000; because
// we see no signals and strange Raspberry behavious.
#define PERIOD_TIME_US_MIN 2000
#define PERIOD_TIME_US_DEFAULT 10000

// The pulse-width-increment will be the same for all channels
#define PULSE_WIDTH_INCREMENT_GRANULARITY_US_DEFAULT 10
