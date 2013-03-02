/*
 * rpio_pwm.c: PWM via DMA for the RaspberryPi, based on the excellent
 * ServoBlaster by Richard Hirst.
 *
 * Documentation
 * =============
 *
 * A server is controlled via the pulse-width within a fixed period (the
 * period is defined by the servo-maker; look it up in the datasheet).
 *
 *      |<--- Period Width (20ms) ------>|
 *
 *      +--------+                       +--------+
 *      |        |                       |        |
 * -----+        +-----------------------+        +------
 *
 *   -->|        |<-- Pulse Width (1..2ms)
 *
 *
 * This documentation is work in progress. Look here for more information:
 * - https://github.com/metachris/raspberrypi-pwm
 * - https://github.com/richardghirst/PiBits/blob/master/ServoBlaster
 *
 *
 * Author: Chris Hager <chris@linuxuser.at>
 * URL: https://github.com/metachris/RPIO
 * License: GPLv3+
 */

#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <string.h>
#include <errno.h>
#include <stdarg.h>
#include <stdint.h>
#include <signal.h>
#include <time.h>
#include <sys/time.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <sys/mman.h>

// 8 GPIOs max
static int gpio_list[8] = {-1, -1, -1, -1, -1, -1, -1, -1};
static int num_gpios = 0;

// PERIOD_TIME_US is the pulse cycle time (period) per servo, in microseconds.
// Typically servos expect it to be 20,000us (20ms). If you are using
// 8 channels (gpios), this results in a 2.5ms timeslot per gpio channel. A
// servo output is set high at the start of its 2.5ms timeslot, and set low
// after the appropriate delay.
#define PERIOD_TIME_US       20000

// PULSE_WIDTH_INCR_US is the pulse width increment granularity, again in microseconds.
// Setting it too low will likely cause problems as the DMA controller will use too much
// memory bandwidth. 10us is a good value, though you might be ok setting it as low as 2us.
#define PULSE_WIDTH_INCR_US  10

// Timeslot per channel (maximum on-time per cycle)
// With this delay it will arrive at the same channel after PERIOD_TIME.
#define CHANNEL_TIME_US      PERIOD_TIME_US

// CHANNEL_SAMPLES is the maximum number of PULSE_WIDTH_INCR_US that fit into one gpio
// channels timeslot. (eg. 250 for a 2500us timeslot with 10us PULSE_WIDTH_INCREMENT)
#define CHANNEL_SAMPLES      (CHANNEL_TIME_US/PULSE_WIDTH_INCR_US)

// Min and max channel width settings (used only for controlling user input)
#define CHANNEL_WIDTH_MIN    0
#define CHANNEL_WIDTH_MAX    (CHANNEL_SAMPLES - 1)

// Various
#define NUM_SAMPLES          (PERIOD_TIME_US/PULSE_WIDTH_INCR_US)
#define NUM_CBS              (NUM_SAMPLES*2)

#define PAGE_SIZE            4096
#define PAGE_SHIFT           12
#define NUM_PAGES            ((NUM_CBS * 32 + NUM_SAMPLES * 4 + \
                              PAGE_SIZE - 1) >> PAGE_SHIFT)

// Memory Addresses
#define DMA_BASE        0x20007000
#define DMA_LEN         0x24
#define PWM_BASE        0x2020C000
#define PWM_LEN         0x28
#define CLK_BASE        0x20101000
#define CLK_LEN         0xA8
#define GPIO_BASE       0x20200000
#define GPIO_LEN        0x100
#define PCM_BASE        0x20203000
#define PCM_LEN         0x24

// Datasheet p. 51:
#define DMA_NO_WIDE_BURSTS  (1<<26)
#define DMA_WAIT_RESP   (1<<3)
#define DMA_D_DREQ      (1<<6)
#define DMA_PER_MAP(x)  ((x)<<16)
#define DMA_END         (1<<1)
#define DMA_RESET       (1<<31)
#define DMA_INT         (1<<2)

// Each DMA channel has 3 writeable registers:
#define DMA_CS          (0x00/4)
#define DMA_CONBLK_AD   (0x04/4)
#define DMA_DEBUG       (0x20/4)

// GPIO Memory Addresses
#define GPIO_FSEL0      (0x00/4)
#define GPIO_SET0       (0x1c/4)
#define GPIO_CLR0       (0x28/4)
#define GPIO_LEV0       (0x34/4)
#define GPIO_PULLEN     (0x94/4)
#define GPIO_PULLCLK    (0x98/4)

// GPIO Modes (IN=0, OUT=1)
#define GPIO_MODE_IN    0
#define GPIO_MODE_OUT   1

// PWM Memory Addresses
#define PWM_CTL         (0x00/4)
#define PWM_DMAC        (0x08/4)
#define PWM_RNG1        (0x10/4)
#define PWM_FIFO        (0x18/4)

#define PWMCLK_CNTL     40
#define PWMCLK_DIV      41

#define PWMCTL_MODE1    (1<<1)
#define PWMCTL_PWEN1    (1<<0)
#define PWMCTL_CLRF     (1<<6)
#define PWMCTL_USEF1    (1<<5)

#define PWMDMAC_ENAB    (1<<31)
#define PWMDMAC_THRSHLD ((15<<8) | (15<<0))

#define PCM_CS_A        (0x00/4)
#define PCM_FIFO_A      (0x04/4)
#define PCM_MODE_A      (0x08/4)
#define PCM_RXC_A       (0x0c/4)
#define PCM_TXC_A       (0x10/4)
#define PCM_DREQ_A      (0x14/4)
#define PCM_INTEN_A     (0x18/4)
#define PCM_INT_STC_A   (0x1c/4)
#define PCM_GRAY        (0x20/4)

#define PCMCLK_CNTL     38
#define PCMCLK_DIV      39

#define DELAY_VIA_PWM   0
#define DELAY_VIA_PCM   1

// DMA Control Block Data Structure (p40): 8 words (256 bits)
typedef struct {
    uint32_t info;   // TI: transfer information
    uint32_t src;    // SOURCE_AD
    uint32_t dst;    // DEST_AD
    uint32_t length; // TXFR_LEN: transfer length
    uint32_t stride; // 2D stride mode
    uint32_t next;   // NEXTCONBK
    uint32_t pad[2]; // _reserved_
} dma_cb_t;

// Holder for all the CB data structure (2 CBs for each sample)
struct ctl {
    uint32_t sample[NUM_SAMPLES];
    dma_cb_t cb[NUM_CBS];
};

typedef struct {
    uint8_t *virtaddr;
    uint32_t physaddr;
} page_map_t;

page_map_t *page_map;

static uint8_t *virtbase;

static volatile uint32_t *pwm_reg;
static volatile uint32_t *pcm_reg;
static volatile uint32_t *clk_reg;
static volatile uint32_t *dma_reg;
static volatile uint32_t *gpio_reg;

static int delay_hw = DELAY_VIA_PWM;

static void set_servo(int servo, int width);

// Sets a GPIO to either GPIO_MODE_IN(=0) or GPIO_MODE_OUT(=1)
static void
gpio_set_mode(uint32_t pin, uint32_t mode)
{
    uint32_t fsel = gpio_reg[GPIO_FSEL0 + pin/10];

    fsel &= ~(7 << ((pin % 10) * 3));
    fsel |= mode << ((pin % 10) * 3);
    gpio_reg[GPIO_FSEL0 + pin/10] = fsel;
}

// Sets the gpio to input (level=1) or output (level=0)
static void
gpio_set(int pin, int level)
{
    if (level)
        gpio_reg[GPIO_SET0] = 1 << pin;
    else
        gpio_reg[GPIO_CLR0] = 1 << pin;
}

// Very short delay
static void
udelay(int us)
{
    struct timespec ts = { 0, us * 1000 };

    nanosleep(&ts, NULL);
}

// Shutdown -- its super important to reset the DMA before quitting
static void
shutdown()
{
    int i;

    if (dma_reg && virtbase) {
        for (i = 0; i < num_gpios; i++)
            if (gpio_list[i] != -1)
                set_servo(i, 0);
        udelay(PERIOD_TIME_US);
        dma_reg[DMA_CS] = DMA_RESET;
        udelay(10);
    }
}

// Terminate is triggered by signals or fatal
static void
terminate()
{
    shutdown();
    exit(1);
}

// Shutdown with an error
static void
fatal(char *fmt, ...)
{
    va_list ap;

    va_start(ap, fmt);
    vfprintf(stderr, fmt, ap);
    va_end(ap);
    terminate();
}

// Catch all signals possible - it is vital we kill the DMA engine
// on process exit!
static void
setup_sighandlers(void)
{
    int i;
    for (i = 0; i < 64; i++) {
        struct sigaction sa;
        memset(&sa, 0, sizeof(sa));
        sa.sa_handler = terminate;
        sigaction(i, &sa, NULL);
    }
}

// Memory mapping
static uint32_t
mem_virt_to_phys(void *virt)
{
    uint32_t offset = (uint8_t *)virt - virtbase;

    return page_map[offset >> PAGE_SHIFT].physaddr + (offset % PAGE_SIZE);
}

// More memory mapping
static void *
map_peripheral(uint32_t base, uint32_t len)
{
    int fd = open("/dev/mem", O_RDWR);
    void * vaddr;

    if (fd < 0)
        fatal("rpio-pwm: Failed to open /dev/mem: %m\n");
    vaddr = mmap(NULL, len, PROT_READ|PROT_WRITE, MAP_SHARED, fd, base);
    if (vaddr == MAP_FAILED)
        fatal("rpio-pwm: Failed to map peripheral at 0x%08x: %m\n", base);
    close(fd);

    return vaddr;
}

// Set one servo to a specific pulse
static void
set_servo(int servo, int width)
{
    int i;
    uint32_t phys_gpclr0 = 0x7e200000 + 0x28;
    uint32_t phys_gpset0 = 0x7e200000 + 0x1c;

    // Base address for control blocks (CB[0])
    struct ctl *ctl = (struct ctl *)virtbase;

    // The servos initial DMA control block
    dma_cb_t *cbp = ctl->cb + servo * CHANNEL_SAMPLES * 2;

    // The servos initial sample setting
    uint32_t *dp = ctl->sample + servo * CHANNEL_SAMPLES;

    // Mask tells the DMA which gpios to set/unset (when it reaches a specific sample)
    uint32_t mask = 1 << gpio_list[servo];

    // Set mask at gpio sample end
    // dp[width] = mask; // done in next block

    // Update all samples for this channel with the respective GPIO-ID
    for (i = 0; i < CHANNEL_SAMPLES; i++) {
        dp[i] = 1 << gpio_list[servo];
    }

    if (width == 0) {
        // Update controlblock dest to clear gpio at sample start
        cbp->dst = phys_gpclr0;
    } else {
        for (i = width - 1; i > 0; i--)
            dp[i] = 0;

        // Set mask at gpio sample startpoint
        dp[0] = mask;

        // Update controlblock dest to set gpio at sample start
        cbp->dst = phys_gpset0;
    }
}

static void
init_ctrl_data(void)
{
    struct ctl *ctl = (struct ctl *)virtbase;
    dma_cb_t *cbp = ctl->cb;
    uint32_t phys_fifo_addr;
    uint32_t phys_gpclr0 = 0x7e200000 + 0x28;
    int i;

    if (delay_hw == DELAY_VIA_PWM)
        phys_fifo_addr = (PWM_BASE | 0x7e000000) + 0x18;
    else
        phys_fifo_addr = (PCM_BASE | 0x7e000000) + 0x04;

    // Reset complete per-sample gpio mask to 0
    memset(ctl->sample, 0, sizeof(ctl->sample));

    // For each sample we add 2 control blocks:
    // - first: clear gpio and jump to second
    // - second: jump to next CB
    for (i = 0; i < NUM_SAMPLES; i++) {
        cbp->info = DMA_NO_WIDE_BURSTS | DMA_WAIT_RESP;
        cbp->src = mem_virt_to_phys(ctl->sample + i);  // src contains mask of which gpios need change at this sample
        cbp->dst = phys_gpclr0;  // set each sample to clear set gpios by default
        cbp->length = 4;
        cbp->stride = 0;
        cbp->next = mem_virt_to_phys(cbp + 1);
        cbp++;

        // Delay
        if (delay_hw == DELAY_VIA_PWM)
            cbp->info = DMA_NO_WIDE_BURSTS | DMA_WAIT_RESP | DMA_D_DREQ | DMA_PER_MAP(5);
        else
            cbp->info = DMA_NO_WIDE_BURSTS | DMA_WAIT_RESP | DMA_D_DREQ | DMA_PER_MAP(2);
        cbp->src = mem_virt_to_phys(ctl); // Any data will do
        cbp->dst = phys_fifo_addr;
        cbp->length = 4;
        cbp->stride = 0;
        cbp->next = mem_virt_to_phys(cbp + 1);
        cbp++;
    }

    // The last control block links back to the first (= endless loop)
    cbp--;
    cbp->next = mem_virt_to_phys(ctl->cb);
}


// Initialize the memory pagemap
static void
make_pagemap(void)
{
    int i, fd, memfd, pid;
    char pagemap_fn[64];

    page_map = malloc(NUM_PAGES * sizeof(*page_map));
    if (page_map == 0)
        fatal("rpio-pwm: Failed to malloc page_map: %m\n");
    memfd = open("/dev/mem", O_RDWR);
    if (memfd < 0)
        fatal("rpio-pwm: Failed to open /dev/mem: %m\n");
    pid = getpid();
    sprintf(pagemap_fn, "/proc/%d/pagemap", pid);
    fd = open(pagemap_fn, O_RDONLY);
    if (fd < 0)
        fatal("rpio-pwm: Failed to open %s: %m\n", pagemap_fn);
    if (lseek(fd, (uint32_t)virtbase >> 9, SEEK_SET) !=
                        (uint32_t)virtbase >> 9) {
        fatal("rpio-pwm: Failed to seek on %s: %m\n", pagemap_fn);
    }
    for (i = 0; i < NUM_PAGES; i++) {
        uint64_t pfn;
        page_map[i].virtaddr = virtbase + i * PAGE_SIZE;
        // Following line forces page to be allocated
        page_map[i].virtaddr[0] = 0;
        if (read(fd, &pfn, sizeof(pfn)) != sizeof(pfn))
            fatal("rpio-pwm: Failed to read %s: %m\n", pagemap_fn);
        if (((pfn >> 55) & 0x1bf) != 0x10c)
            fatal("rpio-pwm: Page %d not present (pfn 0x%016llx)\n", i, pfn);
        page_map[i].physaddr = (uint32_t)pfn << PAGE_SHIFT | 0x40000000;
    }
    close(fd);
    close(memfd);
}

// Initialize PWM (or PCM) and DMA
static void
init_hardware(void)
{
    struct ctl *ctl = (struct ctl *)virtbase;

    if (delay_hw == DELAY_VIA_PWM) {
        // Initialise PWM
        pwm_reg[PWM_CTL] = 0;
        udelay(10);
        clk_reg[PWMCLK_CNTL] = 0x5A000006;        // Source=PLLD (500MHz)
        udelay(100);
        clk_reg[PWMCLK_DIV] = 0x5A000000 | (50<<12);    // set pwm div to 50, giving 10MHz
        udelay(100);
        clk_reg[PWMCLK_CNTL] = 0x5A000016;        // Source=PLLD and enable
        udelay(100);
        pwm_reg[PWM_RNG1] = PULSE_WIDTH_INCR_US * 10;
        udelay(10);
        pwm_reg[PWM_DMAC] = PWMDMAC_ENAB | PWMDMAC_THRSHLD;
        udelay(10);
        pwm_reg[PWM_CTL] = PWMCTL_CLRF;
        udelay(10);
        pwm_reg[PWM_CTL] = PWMCTL_USEF1 | PWMCTL_PWEN1;
        udelay(10);
    } else {
        // Initialise PCM
        pcm_reg[PCM_CS_A] = 1;                // Disable Rx+Tx, Enable PCM block
        udelay(100);
        clk_reg[PCMCLK_CNTL] = 0x5A000006;        // Source=PLLD (500MHz)
        udelay(100);
        clk_reg[PCMCLK_DIV] = 0x5A000000 | (50<<12);    // Set pcm div to 50, giving 10MHz
        udelay(100);
        clk_reg[PCMCLK_CNTL] = 0x5A000016;        // Source=PLLD and enable
        udelay(100);
        pcm_reg[PCM_TXC_A] = 0<<31 | 1<<30 | 0<<20 | 0<<16; // 1 channel, 8 bits
        udelay(100);
        pcm_reg[PCM_MODE_A] = (PULSE_WIDTH_INCR_US * 10 - 1) << 10;
        udelay(100);
        pcm_reg[PCM_CS_A] |= 1<<4 | 1<<3;        // Clear FIFOs
        udelay(100);
        pcm_reg[PCM_DREQ_A] = 64<<24 | 64<<8;        // DMA Req when one slot is free?
        udelay(100);
        pcm_reg[PCM_CS_A] |= 1<<9;            // Enable DMA
        udelay(100);
    }

    // Initialise the DMA channel 0 (p46, 47)
    dma_reg[DMA_CS] = DMA_RESET; // DMA channel reset
    udelay(10);
    dma_reg[DMA_CS] = DMA_INT | DMA_END; // Interrupt status & DMA end flag
    dma_reg[DMA_CONBLK_AD] = mem_virt_to_phys(ctl->cb);  // initial CB
    dma_reg[DMA_DEBUG] = 7; // clear debug error flags
    dma_reg[DMA_CS] = 0x10880001;    // go, mid priority, wait for outstanding writes

    if (delay_hw == DELAY_VIA_PCM) {
        pcm_reg[PCM_CS_A] |= 1<<2;            // Enable Tx
    }
}

// Returns the index in gpio_list of the specified gpio
static int gpio_to_index(int gpio) {
    // Find gpio in index
    int i;
    for (i=0; i<num_gpios; i++) {
        if (gpio_list[i] == gpio)
            return i;
    }
    return -1;
}

// Wrapper for set_servo which uses the gpio-id instead of the gpio_list inde
static void set_gpio(int gpio, int width) {
    // Set the pulse width in us_increments for this gpio
    int index;
    index = gpio_to_index(gpio);
    if (index < 0) {
        fatal("Could not find gpio %s in list of pwm-gpios", gpio);
    }
    set_servo(index, width);
}

// Adds a new gpio-id into the pwm pool, and sets this gpio up as such
static void
add_gpio(int gpio) {
    int gpio_index;

    printf("Adding gpio %d to pwm system\n", gpio);
    if (num_gpios == sizeof(gpio_list)) {
        fatal("Cannot add more gpios (max reached)");
    }

    gpio_index = num_gpios;
    num_gpios += 1;
    printf("- gpio index %d", gpio_index);

    gpio_list[gpio_index] = gpio;
    gpio_set(gpio, 0);
    printf("x1 - ");
    gpio_set_mode(gpio, GPIO_MODE_OUT);
    printf("x2 - ");
    set_servo(gpio_index, 0);
    printf("x4 - ");
}

// Removes a gpio from the pwm pool
static void
del_gpio(int gpio) {
    int gpio_index;
    gpio_index = gpio_to_index(gpio);
    if (gpio_index == -1) {
        fatal("Could not delete gpio %s from pwm, no such gpio", gpio);
    }
    set_servo(gpio_index, 0);
    gpio_list[gpio_index] = -1;
}

int
main(int argc, char **argv)
{
    // Very crude...
    if (argc == 2 && !strcmp(argv[1], "--pcm"))
        delay_hw = DELAY_VIA_PCM;

    printf("Using hardware:       %s\n", delay_hw == DELAY_VIA_PWM ? "PWM" : "PCM");
    //printf("Number of servos:     %d\n", NUM_GPIOS);
    printf("Servo cycle time:     %dus\n", PERIOD_TIME_US);
    printf("Pulse width units:    %dus\n", PULSE_WIDTH_INCR_US);
    printf("Maximum width value:  %d (%dus)\n", CHANNEL_WIDTH_MAX,
                        CHANNEL_WIDTH_MAX * PULSE_WIDTH_INCR_US);

    setup_sighandlers();

    dma_reg = map_peripheral(DMA_BASE, DMA_LEN);
    pwm_reg = map_peripheral(PWM_BASE, PWM_LEN);
    pcm_reg = map_peripheral(PCM_BASE, PCM_LEN);
    clk_reg = map_peripheral(CLK_BASE, CLK_LEN);
    gpio_reg = map_peripheral(GPIO_BASE, GPIO_LEN);

    virtbase = mmap(NULL, NUM_PAGES * PAGE_SIZE, PROT_READ|PROT_WRITE,
            MAP_SHARED|MAP_ANONYMOUS|MAP_NORESERVE|MAP_LOCKED,
            -1, 0);
    if (virtbase == MAP_FAILED)
        fatal("rpio-pwm: Failed to mmap physical pages: %m\n");
    if ((unsigned long)virtbase & (PAGE_SIZE-1))
        fatal("rpio-pwm: Virtual address is not page aligned\n");

    make_pagemap();

    //for (i = 0; i < NUM_GPIOS; i++) {
    //    gpio_set(gpio_list[i], 0);
    //    gpio_set_mode(gpio_list[i], GPIO_MODE_OUT);
    //}

    init_ctrl_data();
    init_hardware();

#define TIMEOUT 30000000

    // Add something blocking here
    add_gpio(17);

    printf("- 200\n");
    set_gpio(17, 200);
    usleep(TIMEOUT);

    shutdown(0);
    exit(0);

    printf("- 100\n");
    set_gpio(17, 100);
    usleep(TIMEOUT);

    printf("- 50\n");
    set_gpio(17, 50);
    usleep(TIMEOUT);

    printf("- 10\n");
    set_gpio(17, 10);
    usleep(TIMEOUT);

    printf("- 50\n");
    set_gpio(17, 50);
    usleep(TIMEOUT);

    printf("- 100\n");
    set_gpio(17, 100);
    usleep(TIMEOUT);

    printf("- 200\n");
    set_gpio(17, 200);
    usleep(TIMEOUT);

    printf("Delete gpio 17\n");
    del_gpio(17);

    printf("\nTESTS2\n");
    printf("Adding gpio 17\n");
    add_gpio(17);

    printf("- 100\n");
    set_gpio(17, 100);
    usleep(TIMEOUT);

    printf("Adding gpio 17 a second time\n");
    add_gpio(17);

    printf("All done.\n");

    // terminate
    shutdown(0);

    printf("done\n");
    return 0;
}
