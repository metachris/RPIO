/*
 * This file is part of RPIO.
 *
 * License: GPLv3+
 * Author: Chris Hager <chris@linuxuser.at>
 * URL: https://github.com/metachris/RPIO
 *
 * Flexible PWM via DMA for the Raspberry Pi. Multiple DMA channels are
 * supported. You can use PCM instead of PWM with the "--pcm" argument.
 *
 * Based on the excellent servod.c by Richard Hirst.
 *
 * Build it with `gcc -Wall -g -O2 -o pwm pwm.c`
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
#include "pwm.h"

// 8 GPIOs max; one GPIO uses one DMA channel
#define MAX_GPIOS 8
static int gpio_list[MAX_GPIOS];

// Standard page sizes
#define PAGE_SIZE       4096
#define PAGE_SHIFT      12

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
    uint32_t gpio_mask;
    uint32_t period_time_us;

    // Set by system
    uint32_t num_samples;
    uint32_t num_cbs;
    uint32_t num_pages;

    // Used only for control purposes
    uint32_t width_max;
};

// One control structure per channel
static struct channel channels[MAX_GPIOS];

// Common registers
static volatile uint32_t *pwm_reg;
static volatile uint32_t *pcm_reg;
static volatile uint32_t *clk_reg;
static volatile uint32_t *gpio_reg;

// Default timer hardware is PWM
static int delay_hw = DELAY_VIA_PWM;

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

// Very short delay as demanded per datasheet
static void
udelay(int us)
{
    struct timespec ts = { 0, us * 1000 };

    nanosleep(&ts, NULL);
}

// Shutdown -- its important to reset the DMA before quitting
void
shutdown(void)
{
    int i;

    for (i = 0; i < MAX_GPIOS; i++) {
        if (channels[i].dma_reg && channels[i].virtbase) {
            printf("shutdown channel %d\n", i);
            set_channel_pulse(i, 0);
            udelay(channels[i].period_time_us);
            channels[i].dma_reg[DMA_CS] = DMA_RESET;
            udelay(10);
        }
    }
}

// Terminate is triggered by signals or fatal
static void
terminate(void)
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
        sa.sa_handler = (void *) terminate;
        sigaction(i, &sa, NULL);
    }
}

// Memory mapping
static uint32_t
mem_virt_to_phys(int channel, void *virt)
{
    uint32_t offset = (uint8_t *)virt - channels[channel].virtbase;
    return channels[channel].page_map[offset >> PAGE_SHIFT].physaddr + (offset % PAGE_SIZE);
}

// Peripherals memory mapping
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

// Returns a pointer to the control block of this channel in DMA memory
uint8_t* get_cb(int channel)
{
    return channels[channel].virtbase + (sizeof(uint32_t) * channels[channel].num_samples);
}

// Set channel to a specific initial pulse (this also clears all other pulses).
// pulse-width-us = width * pulse_width_incr_us
void
set_channel_pulse(int channel, int width)
{
    int i;
    uint32_t phys_gpclr0 = 0x7e200000 + 0x28;
    uint32_t phys_gpset0 = 0x7e200000 + 0x1c;

    dma_cb_t *cbp = (dma_cb_t *) get_cb(channel);
    uint32_t *dp = (uint32_t *) channels[channel].virtbase;

    // Mask tells the DMA which gpios to set/unset (when it reaches a specific sample)
    uint32_t mask = 1 << gpio_list[channel];

    printf("set_channel_pulse: channel=%d, width=%d\n", channel, width);

    // Update all samples for this channel with the respective GPIO-ID
    for (i = 0; i < channels[channel].num_samples; i++) {
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


// Update the channel with another pulse within one full cycle
void
add_channel_pulse(int channel, int width_start, int width)
{
    int i;
    uint32_t phys_gpclr0 = 0x7e200000 + 0x28;
    uint32_t phys_gpset0 = 0x7e200000 + 0x1c;

    dma_cb_t *cbp = (dma_cb_t *) get_cb(channel) + (width_start * 2);
    uint32_t *dp = (uint32_t *) channels[channel].virtbase;

    // Mask tells the DMA which gpios to set/unset (when it reaches a specific sample)
    uint32_t mask = 1 << gpio_list[channel];

    printf("update_channel_pulse: channel=%d, start=%d, width=%d\n", channel, width_start, width);

    // enable or disable gpio at this point in the cycle
    *(dp + width_start) = mask;
    cbp->dst = phys_gpset0;

    // Do nothing for the specified width
    for (i = 1; i < width - 1; i++) {
        *(dp + width_start + i) = 0;
        cbp += 2;
    }

    // Clear GPIO at end
    *(dp + width_start + width) = mask;
    cbp->dst = phys_gpclr0;
}



// Get a channel's pagemap
static void
make_pagemap(int channel)
{
    int i, fd, memfd, pid;
    char pagemap_fn[64];

    channels[channel].page_map = malloc(channels[channel].num_pages * sizeof(*channels[channel].page_map));

    if (channels[channel].page_map == 0)
        fatal("rpio-pwm: Failed to malloc page_map: %m\n");
    memfd = open("/dev/mem", O_RDWR);
    if (memfd < 0)
        fatal("rpio-pwm: Failed to open /dev/mem: %m\n");
    pid = getpid();
    sprintf(pagemap_fn, "/proc/%d/pagemap", pid);
    fd = open(pagemap_fn, O_RDONLY);
    if (fd < 0)
        fatal("rpio-pwm: Failed to open %s: %m\n", pagemap_fn);
    if (lseek(fd, (uint32_t)channels[channel].virtbase >> 9, SEEK_SET) !=
                        (uint32_t)channels[channel].virtbase >> 9) {
        fatal("rpio-pwm: Failed to seek on %s: %m\n", pagemap_fn);
    }
    for (i = 0; i < channels[channel].num_pages; i++) {
        uint64_t pfn;
        channels[channel].page_map[i].virtaddr = channels[channel].virtbase + i * PAGE_SIZE;
        // Following line forces page to be allocated
        channels[channel].page_map[i].virtaddr[0] = 0;
        if (read(fd, &pfn, sizeof(pfn)) != sizeof(pfn))
            fatal("rpio-pwm: Failed to read %s: %m\n", pagemap_fn);
        if (((pfn >> 55) & 0x1bf) != 0x10c)
            fatal("rpio-pwm: Page %d not present (pfn 0x%016llx)\n", i, pfn);
        channels[channel].page_map[i].physaddr = (uint32_t)pfn << PAGE_SHIFT | 0x40000000;
    }
    close(fd);
    close(memfd);
}

static void
init_virtbase(int channel)
{
    channels[channel].virtbase = mmap(NULL, channels[channel].num_pages * PAGE_SIZE, PROT_READ|PROT_WRITE,
            MAP_SHARED|MAP_ANONYMOUS|MAP_NORESERVE|MAP_LOCKED, -1, 0);
    if (channels[channel].virtbase == MAP_FAILED)
        fatal("rpio-pwm: Failed to mmap physical pages: %m\n");
    if ((unsigned long)channels[channel].virtbase & (PAGE_SIZE-1))
        fatal("rpio-pwm: Virtual address is not page aligned\n");
}

// Initialize control block for this channel
static void
init_ctrl_data(int channel)
{
    dma_cb_t *cbp = (dma_cb_t *) get_cb(channel);
    uint32_t *sample = (uint32_t *) channels[channel].virtbase;

    uint32_t phys_fifo_addr;
    uint32_t phys_gpclr0 = 0x7e200000 + 0x28;
    int i;

    channels[channel].dma_reg = map_peripheral(DMA_BASE, DMA_LEN) + (DMA_CHANNEL_INC * channel);

    if (delay_hw == DELAY_VIA_PWM)
        phys_fifo_addr = (PWM_BASE | 0x7e000000) + 0x18;
    else
        phys_fifo_addr = (PCM_BASE | 0x7e000000) + 0x04;

    // Reset complete per-sample gpio mask to 0
    memset(sample, 0, sizeof(channels[channel].num_samples * sizeof(uint32_t)));

    // For each sample we add 2 control blocks:
    // - first: clear gpio and jump to second
    // - second: jump to next CB
    for (i = 0; i < channels[channel].num_samples; i++) {
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
    channels[channel].dma_reg[DMA_CS] = DMA_RESET; // DMA channel reset
    udelay(10);
    channels[channel].dma_reg[DMA_CS] = DMA_INT | DMA_END; // Interrupt status & DMA end flag
    channels[channel].dma_reg[DMA_CONBLK_AD] = mem_virt_to_phys(channel, get_cb(channel));  // initial CB
    channels[channel].dma_reg[DMA_DEBUG] = 7; // clear debug error flags
    channels[channel].dma_reg[DMA_CS] = 0x10880001;    // go, mid priority, wait for outstanding writes
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

// Setup a channel with a specific period time. After that pulse-widths can be
// changed at any time.
void
init_channel(int channel, int gpio, int period_time_us)
{
    printf("Initializing channel %d...\n", channel);

    // Setup Data
    channels[channel].period_time_us = period_time_us;
    channels[channel].num_samples = channels[channel].period_time_us / pulse_width_incr_us;
    channels[channel].width_max = channels[channel].num_samples - 1;
    channels[channel].num_cbs = channels[channel].num_samples * 2;
    channels[channel].num_pages = ((channels[channel].num_cbs * 32 + channels[channel].num_samples * 4 + \
                                       PAGE_SIZE - 1) >> PAGE_SHIFT);

    // Initialize channel
    init_virtbase(channel);
    make_pagemap(channel);
    init_ctrl_data(channel);

    // Set GPIO
    gpio_list[channel] = gpio;
    gpio_set(gpio, 0);
    gpio_set_mode(gpio, GPIO_MODE_OUT);
}

// Print some info about a channel
void
print_channel(int channel)
{
    printf("Period time:   %dus\n", channels[channel].period_time_us);
    printf("PW Increments: %dus\n\n", pulse_width_incr_us);
    printf("Num samples:   %d\n", channels[channel].num_samples);
    printf("Num CBS:       %d\n", channels[channel].num_cbs);
    printf("Num pages:     %d\n", channels[channel].num_pages);
}

// hw: 0=PWM, 1=PCM
int
setup(int pw_incr_us, int hw)
{
    int i;

    delay_hw = hw;
    pulse_width_incr_us = pw_incr_us;
    printf("Using hardware: %s\n", delay_hw == DELAY_VIA_PWM ? "PWM" : "PCM");
    printf("PW increments:  %dus\n", pulse_width_incr_us);

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
    return 1;
}

int
main(int argc, char **argv)
{
    // Very crude...
    if (argc == 2 && !strcmp(argv[1], "--pcm"))
        setup(pulse_width_incr_us, DELAY_VIA_PCM);
    else
        setup(pulse_width_incr_us, DELAY_VIA_PWM);

    // Setup channel
    int gpio = 17;
    int channel = 0;
    int period_time_us = 10000;
    init_channel(channel, gpio, period_time_us);
    print_channel(channel);

    // Use the channel for various pulse widths
    const int demo_timeout = 5 * 1000000;  // 5 seconds
    set_channel_pulse(channel, 50);
    add_channel_pulse(0, 100, 50);
    add_channel_pulse(0, 200, 50);
    add_channel_pulse(0, 300, 50);
    usleep(demo_timeout);
//    set_channel_pulse(channel, 10);
//    usleep(demo_timeout);
//    set_channel_pulse(channel, 50);
//    usleep(demo_timeout);

    // All done
    shutdown();
    exit(0);
}
