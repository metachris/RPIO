int setup(void);
void setup_gpio(int gpio, int direction, int pud);
void output_gpio(int gpio, int value);
int input_gpio(int gpio);
void cleanup(void);
int gpio_function(int gpio);

#define SETUP_OK          0
#define SETUP_DEVMEM_FAIL 1
#define SETUP_MALLOC_FAIL 2
#define SETUP_MMAP_FAIL   3

#define INPUT  1 // is really 0 for control register!
#define OUTPUT 0 // is really 1 for control register!
#define ALT0   4

#define HIGH 1
#define LOW  0

#define PUD_OFF  0
#define PUD_DOWN 1
#define PUD_UP   2
