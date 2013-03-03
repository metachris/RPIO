/*
 * This file is part of RPIO.
 *
 * License: GPLv3+
 * Author: Chris Hager <chris@linuxuser.at>
 * URL: https://github.com/metachris/RPIO
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
#define MAX_GPIOS 8 // one GPIO uses 1 DMA channel
static int gpio_list[MAX_GPIOS];
//static int num_gpios = 0;

// Standard page sizes
#define PAGE_SIZE            4096
#define PAGE_SHIFT           12

// Memory Addresses
#define DMA_BASE        0x20007000
#define DMA_CHANNEL_INC 0x100
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

// Memory mapping
typedef struct {
    uint8_t *virtaddr;
    uint32_t physaddr;
} page_map_t;

// Main control structure per channel
struct channel {
    uint8_t *virtbase;
    uint32_t *sample;
    dma_cb_t *cb;
    page_map_t *page_map;
    volatile uint32_t *dma_reg;

    // Set by user
    uint32_t period_time_us;
    uint32_t pulse_width;

    // Set by system
    uint32_t num_samples;
    uint32_t num_cbs;
    uint32_t num_pages;
};

// One control structure per channel
static struct channel channel_arr[MAX_GPIOS];
static uint8_t pulse_width_incr_us = 10;

// Common registers
static volatile uint32_t *pwm_reg;
static volatile uint32_t *pcm_reg;
static volatile uint32_t *clk_reg;
static volatile uint32_t *gpio_reg;

static int delay_hw = DELAY_VIA_PWM;

static void set_channel_pulse(int channel, int width);

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

    for (i = 0; i < MAX_GPIOS; i++) {
        if (channel_arr[i].dma_reg && channel_arr[i].virtbase) {
            printf("shutdown channel %d\n", i);
            set_channel_pulse(i, 0);
            udelay(channel_arr[i].period_time_us);
            channel_arr[i].dma_reg[DMA_CS] = DMA_RESET;
            udelay(10);
        }
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
mem_virt_to_phys(int channel, void *virt)
{
    uint32_t offset = (uint8_t *)virt - channel_arr[channel].virtbase;
    return channel_arr[channel].page_map[offset >> PAGE_SHIFT].physaddr + (offset % PAGE_SIZE);
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

// Returns the pointer to the control block in DMA memory
uint8_t* get_cb(int channel) {
    return channel_arr[channel].virtbase + (sizeof(uint32_t) * channel_arr[channel].num_samples);
}

// Set one servo to a specific pulse
static void
set_channel_pulse(int channel, int width)
{
    int i;
    uint32_t phys_gpclr0 = 0x7e200000 + 0x28;
    uint32_t phys_gpset0 = 0x7e200000 + 0x1c;

    // The servos initial DMA control block
    dma_cb_t *cbp = (dma_cb_t *) get_cb(channel);

    // The servos initial sample setting
    uint32_t *dp = (uint32_t *) channel_arr[channel].virtbase;

    // Mask tells the DMA which gpios to set/unset (when it reaches a specific sample)
    uint32_t mask = 1 << gpio_list[channel];

    // Update all samples for this channel with the respective GPIO-ID
    for (i = 0; i < channel_arr[channel].num_samples; i++) {
        *(dp + i) = 1 << gpio_list[channel];
    }

    if (width == 0) {
        // Update controlblock dest to clear gpio at sample start
        cbp->dst = phys_gpclr0;
    } else {
        for (i = width - 1; i > 0; i--)
            *(dp + i) = 0;

        // Set mask at gpio sample startpoint
        *dp = mask;

        // Update controlblock dest to set gpio at sample start
        cbp->dst = phys_gpset0;
    }
}


// Initialize the memory pagemap
static void
make_pagemap(int channel)
{
    int i, fd, memfd, pid;
    char pagemap_fn[64];

//    printf("make_pagemap: num_pages=%d\n", channel_arr[channel].num_pages);
    channel_arr[channel].page_map = malloc(channel_arr[channel].num_pages * sizeof(*channel_arr[channel].page_map));

    if (channel_arr[channel].page_map == 0)
        fatal("rpio-pwm: Failed to malloc page_map: %m\n");
    memfd = open("/dev/mem", O_RDWR);
    if (memfd < 0)
        fatal("rpio-pwm: Failed to open /dev/mem: %m\n");
    pid = getpid();
    sprintf(pagemap_fn, "/proc/%d/pagemap", pid);
    fd = open(pagemap_fn, O_RDONLY);
    if (fd < 0)
        fatal("rpio-pwm: Failed to open %s: %m\n", pagemap_fn);
    if (lseek(fd, (uint32_t)channel_arr[channel].virtbase >> 9, SEEK_SET) !=
                        (uint32_t)channel_arr[channel].virtbase >> 9) {
        fatal("rpio-pwm: Failed to seek on %s: %m\n", pagemap_fn);
    }
    for (i = 0; i < channel_arr[channel].num_pages; i++) {
        uint64_t pfn;
        channel_arr[channel].page_map[i].virtaddr = channel_arr[channel].virtbase + i * PAGE_SIZE;
        // Following line forces page to be allocated
        channel_arr[channel].page_map[i].virtaddr[0] = 0;
        if (read(fd, &pfn, sizeof(pfn)) != sizeof(pfn))
            fatal("rpio-pwm: Failed to read %s: %m\n", pagemap_fn);
        if (((pfn >> 55) & 0x1bf) != 0x10c)
            fatal("rpio-pwm: Page %d not present (pfn 0x%016llx)\n", i, pfn);
        channel_arr[channel].page_map[i].physaddr = (uint32_t)pfn << PAGE_SHIFT | 0x40000000;
    }
    close(fd);
    close(memfd);
}

static void
init_virtbase(int channel) {
    channel_arr[channel].virtbase = mmap(NULL, channel_arr[channel].num_pages * PAGE_SIZE, PROT_READ|PROT_WRITE,
            MAP_SHARED|MAP_ANONYMOUS|MAP_NORESERVE|MAP_LOCKED, -1, 0);
    if (channel_arr[channel].virtbase == MAP_FAILED)
        fatal("rpio-pwm: Failed to mmap physical pages: %m\n");
    if ((unsigned long)channel_arr[channel].virtbase & (PAGE_SIZE-1))
        fatal("rpio-pwm: Virtual address is not page aligned\n");
}

static void
init_ctrl_data(int channel)
{
    dma_cb_t *cbp = (dma_cb_t *) get_cb(channel);
    uint32_t *sample = (uint32_t *) channel_arr[channel].virtbase;

    uint32_t phys_fifo_addr;
    uint32_t phys_gpclr0 = 0x7e200000 + 0x28;
    int i;

    channel_arr[channel].dma_reg = map_peripheral(DMA_BASE, DMA_LEN) + (DMA_CHANNEL_INC * channel);

    if (delay_hw == DELAY_VIA_PWM)
        phys_fifo_addr = (PWM_BASE | 0x7e000000) + 0x18;
    else
        phys_fifo_addr = (PCM_BASE | 0x7e000000) + 0x04;

    // Reset complete per-sample gpio mask to 0
    memset(sample, 0, sizeof(channel_arr[channel].num_samples * sizeof(uint32_t)));

    // For each sample we add 2 control blocks:
    // - first: clear gpio and jump to second
    // - second: jump to next CB
    for (i = 0; i < channel_arr[channel].num_samples; i++) {
        cbp->info = DMA_NO_WIDE_BURSTS | DMA_WAIT_RESP;
        cbp->src = mem_virt_to_phys(channel, sample + i);  // src contains mask of which gpios need change at this sample
        cbp->dst = phys_gpclr0;  // set each sample to clear set gpios by default
        cbp->length = 4;
        cbp->stride = 0;
        cbp->next = mem_virt_to_phys(channel, cbp + 1);
        cbp++;

        // Delay
        if (delay_hw == DELAY_VIA_PWM)
            cbp->info = DMA_NO_WIDE_BURSTS | DMA_WAIT_RESP | DMA_D_DREQ | DMA_PER_MAP(5);
        else
            cbp->info = DMA_NO_WIDE_BURSTS | DMA_WAIT_RESP | DMA_D_DREQ | DMA_PER_MAP(2);
        cbp->src = mem_virt_to_phys(channel, sample); // Any data will do
        cbp->dst = phys_fifo_addr;
        cbp->length = 4;
        cbp->stride = 0;
        cbp->next = mem_virt_to_phys(channel, cbp + 1);
        cbp++;
    }

    // The last control block links back to the first (= endless loop)
    cbp--;
    cbp->next = mem_virt_to_phys(channel, get_cb(channel));

    // Initialize the DMA channel 0 (p46, 47)
    channel_arr[channel].dma_reg[DMA_CS] = DMA_RESET; // DMA channel reset
    udelay(10);
    channel_arr[channel].dma_reg[DMA_CS] = DMA_INT | DMA_END; // Interrupt status & DMA end flag
    channel_arr[channel].dma_reg[DMA_CONBLK_AD] = mem_virt_to_phys(channel, get_cb(channel));  // initial CB
    channel_arr[channel].dma_reg[DMA_DEBUG] = 7; // clear debug error flags
    channel_arr[channel].dma_reg[DMA_CS] = 0x10880001;    // go, mid priority, wait for outstanding writes
}

// Initialize PWM or PCM hardware once for all channels (10MHz)
static void
init_hardware(void)
{
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
        pwm_reg[PWM_RNG1] = pulse_width_incr_us * 10;
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
        pcm_reg[PCM_MODE_A] = (pulse_width_incr_us * 10 - 1) << 10;
        udelay(100);
        pcm_reg[PCM_CS_A] |= 1<<4 | 1<<3;        // Clear FIFOs
        udelay(100);
        pcm_reg[PCM_DREQ_A] = 64<<24 | 64<<8;        // DMA Req when one slot is free?
        udelay(100);
        pcm_reg[PCM_CS_A] |= 1<<9;            // Enable DMA
        udelay(100);
        pcm_reg[PCM_CS_A] |= 1<<2;            // Enable Tx
    }
}

// Returns the index in gpio_list of the specified gpio
//static int
//gpio_to_index(int gpio) {
//    // Find gpio in index
//    int i;
//    for (i=0; i<MAX_GPIOS; i++) {
//        if (gpio_list[i] == gpio)
//            return i;
//    }
//    return -1;
//}

// Wrapper for set_servo which uses the gpio-id instead of the gpio_list inde
//static void
//set_gpio(int gpio, int width) {
//    // Set the pulse width in us_increments for this gpio
//    int index;
//    index = gpio_to_index(gpio);
//    if (index < 0) {
//        fatal("Could not find gpio %s in list of pwm-gpios", gpio);
//    }
//    set_servo(index, width);
//}

// Adds a new gpio-id into the pwm pool, and sets this gpio up as such
//static void
//add_gpio(int gpio) {
//    int gpio_index;
//
//    printf("Adding gpio %d to pwm system\n", gpio);
//    if (num_gpios == sizeof(MAX_GPIOS)) {
//        fatal("Cannot add more gpios (max reached)");
//    }
//
//    gpio_index = num_gpios;
//    num_gpios += 1;
//    printf("- gpio index %d\n", gpio_index);
//
//    gpio_list[gpio_index] = gpio;
//    gpio_set(gpio, 0);
//    gpio_set_mode(gpio, GPIO_MODE_OUT);
//    set_servo(gpio_index, 0);
//}

// Removes a gpio from the pwm pool
//static void
//del_gpio(int gpio) {
//    int gpio_index;
//    gpio_index = gpio_to_index(gpio);
//    if (gpio_index == -1) {
//        fatal("Could not delete gpio %s from pwm, no such gpio", gpio);
//    }
//    set_servo(gpio_index, 0);
//    gpio_list[gpio_index] = -1;
//}


// Takes care of initializing one channel (virtbase, pagemap, ctrl_data)
// all these steps need to be taken when changing pulse/period widths
static void
init_channel(int channel, int gpio, int pulse_width, int pause_width)
{
    printf("Initializing channel %d...\n", channel);

    // Setup Data
    channel_arr[channel].pulse_width = pulse_width;
    channel_arr[channel].period_time_us = (pulse_width + pause_width) * pulse_width_incr_us;
    channel_arr[channel].num_samples = channel_arr[channel].period_time_us / pulse_width_incr_us;
    channel_arr[channel].num_cbs = channel_arr[channel].num_samples * 2;
    channel_arr[channel].num_pages = ((channel_arr[channel].num_cbs * 32 + channel_arr[channel].num_samples * 4 + \
                                       PAGE_SIZE - 1) >> PAGE_SHIFT);

    // Initialize channel
    init_virtbase(channel);
    make_pagemap(channel);
    init_ctrl_data(channel);

    // Set GPIO
    gpio_list[channel] = gpio;
    gpio_set(gpio, 0);
    gpio_set_mode(gpio, GPIO_MODE_OUT);
    set_channel_pulse(channel, pulse_width);
}

static void
print_channel(int channel)
{
    printf("Pulse time:   %dus\n", channel_arr[channel].pulse_width * pulse_width_incr_us);
    printf("Period time:  %dus\n\n", channel_arr[channel].period_time_us);
    printf("Num samples:  %d\n", channel_arr[channel].num_samples);
    printf("Num CBS:      %d\n", channel_arr[channel].num_cbs);
    printf("Num pages:    %d\n", channel_arr[channel].num_pages);
}

int
main(int argc, char **argv)
{
    int i;

    // Very crude...
    if (argc == 2 && !strcmp(argv[1], "--pcm"))
        delay_hw = DELAY_VIA_PCM;

    printf("Using hardware:       %s\n", delay_hw == DELAY_VIA_PWM ? "PWM" : "PCM");

    // initialize gpio list
    for (i=0; i<sizeof(MAX_GPIOS); i++)
        gpio_list[i] = -1;

    // Catch all kind of kill signals
    setup_sighandlers();

    // Initialize common stuff
    pcm_reg = map_peripheral(PCM_BASE, PCM_LEN);
    clk_reg = map_peripheral(CLK_BASE, CLK_LEN);
    gpio_reg = map_peripheral(GPIO_BASE, GPIO_LEN);
    pwm_reg = map_peripheral(PWM_BASE, PWM_LEN);
    init_hardware();

    // CUSTOM PROGRAM //
#define TIMEOUT 10000000

    // SETUP CHANNEL
    int gpio = 17;
    int channel = 0;
    int pulse_width = 20;
    int pause_width = 800;
    init_channel(channel, gpio, pulse_width, pause_width);
    print_channel(channel);

    // Wait a bit now
    usleep(TIMEOUT);

    shutdown();
    printf("finished\n");
    exit(0);
}
