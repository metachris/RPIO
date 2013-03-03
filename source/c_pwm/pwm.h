int setup(int hw);
static void shutdown();
static void init_channel(int channel, int gpio, int period_time_us);
static void set_channel_pulse(int channel, int width);

#define DELAY_VIA_PWM   0
#define DELAY_VIA_PCM   1
