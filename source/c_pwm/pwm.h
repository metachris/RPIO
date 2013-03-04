int setup(int hw, int pw_incr_us);
void shutdown(void);
void init_channel(int channel, int gpio, int period_time_us);
void set_channel_pulse(int channel, int width);
void print_channel(int channel);

#define DELAY_VIA_PWM   0
#define DELAY_VIA_PCM   1

// This pulse-width-increment must be the same for all channels
static uint8_t pulse_width_incr_us = 10;
