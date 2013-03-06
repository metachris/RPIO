/*
 * This file is part of RPIO.
 *
 * License: GPLv3+
 * Author: Chris Hager <chris@linuxuser.at>
 * URL: https://github.com/metachris/RPIO
 */
int setup(int pw_incr_us, int hw);
void shutdown(void);
void set_loglevel(int level);

int init_channel(int channel, int subcycle_time_us);
int clear_channel_pulses(int channel);
int print_channel(int channel);

int add_channel_pulse(int channel, int gpio, int width_start, int width);
char* get_error_message(void);
void set_softfatal(int enabled);


#define DELAY_VIA_PWM   0
#define DELAY_VIA_PCM   1

#define LOG_LEVEL_DEBUG 0
#define LOG_LEVEL_ERRORS 1
#define LOG_LEVEL_DEFAULT LOG_LEVEL_DEBUG

// Subcycle defaults to 10ms within which you can add any number of pulses
#define SUBCYCLE_TIME_US_DEFAULT 10000

// Subcycle cannot be lower than 2000. We kept seeing no signals and strange
// behavior of the Raspberry Pi (eg. bash fail, reboot).
#define SUBCYCLE_TIME_US_MIN 2000

// The pulse-width-increment-granularity is the same for all channels
#define PULSE_WIDTH_INCREMENT_GRANULARITY_US_DEFAULT 10
