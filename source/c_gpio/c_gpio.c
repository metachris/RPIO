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
 *
 *
 * c_gpio.c is based on RPi.GPIO by Ben Croston, and provides a Python interface to
 * interact with the gpio-related C methods.
 */
#include <stdint.h>
#include <stdlib.h>
#include <fcntl.h>
#include <sys/mman.h>
#include "c_gpio.h"

#define BCM2708_PERI_BASE   0x20000000
#define GPIO_BASE           (BCM2708_PERI_BASE + 0x200000)
#define OFFSET_FSEL         0   // 0x0000
#define OFFSET_SET          7   // 0x001c / 4
#define OFFSET_CLR          10  // 0x0028 / 4
#define OFFSET_PINLEVEL     13  // 0x0034 / 4
#define OFFSET_PULLUPDN     37  // 0x0094 / 4
#define OFFSET_PULLUPDNCLK  38  // 0x0098 / 4

// Event detection offsets disabled for now
//#define OFFSET_EVENT_DETECT 16  // 0x0040 / 4
//#define OFFSET_RISING_ED    19  // 0x004c / 4
//#define OFFSET_FALLING_ED   22  // 0x0058 / 4
//#define OFFSET_HIGH_DETECT  25  // 0x0064 / 4
//#define OFFSET_LOW_DETECT   28  // 0x0070 / 4

#define PAGE_SIZE  (4*1024)
#define BLOCK_SIZE (4*1024)

static volatile uint32_t *gpio_map;

// `short_wait` waits 150 cycles
void
short_wait(void)
{
    int i;
    for (i=0; i<150; i++) {
        asm volatile("nop");
    }
}

// `setup` is run when GPIO is imported in Python
int
setup(void)
{
    int mem_fd;
    uint8_t *gpio_mem;

    if ((mem_fd = open("/dev/mem", O_RDWR|O_SYNC) ) < 0)
        return SETUP_DEVMEM_FAIL;

    if ((gpio_mem = malloc(BLOCK_SIZE + (PAGE_SIZE-1))) == NULL)
        return SETUP_MALLOC_FAIL;

    if ((uint32_t)gpio_mem % PAGE_SIZE)
        gpio_mem += PAGE_SIZE - ((uint32_t)gpio_mem % PAGE_SIZE);

    gpio_map = (uint32_t *)mmap( (caddr_t)gpio_mem, BLOCK_SIZE, PROT_READ|PROT_WRITE, MAP_SHARED|MAP_FIXED, mem_fd, GPIO_BASE);

    if ((uint32_t)gpio_map < 0)
        return SETUP_MMAP_FAIL;

    return SETUP_OK;
}

// Sets a pullup or -down resistor on a GPIO
void
set_pullupdn(int gpio, int pud)
{
    int clk_offset = OFFSET_PULLUPDNCLK + (gpio/32);
    int shift = (gpio%32);

    if (pud == PUD_DOWN)
       *(gpio_map+OFFSET_PULLUPDN) = (*(gpio_map+OFFSET_PULLUPDN) & ~3) | PUD_DOWN;
    else if (pud == PUD_UP)
       *(gpio_map+OFFSET_PULLUPDN) = (*(gpio_map+OFFSET_PULLUPDN) & ~3) | PUD_UP;
    else  // pud == PUD_OFF
       *(gpio_map+OFFSET_PULLUPDN) &= ~3;

    short_wait();
    *(gpio_map+clk_offset) = 1 << shift;
    short_wait();
    *(gpio_map+OFFSET_PULLUPDN) &= ~3;
    *(gpio_map+clk_offset) = 0;
}

// Sets a GPIO to either output or input (input can have an optional pullup
// or -down resistor).
void
setup_gpio(int gpio, int direction, int pud)
{
    int offset = OFFSET_FSEL + (gpio/10);
    int shift = (gpio%10)*3;

    set_pullupdn(gpio, pud);
    if (direction == OUTPUT)
        *(gpio_map+offset) = (*(gpio_map+offset) & ~(7<<shift)) | (1<<shift);
    else  // direction == INPUT
        *(gpio_map+offset) = (*(gpio_map+offset) & ~(7<<shift));
}

// Returns the function of a GPIO: 0=input, 1=output, 4=alt0
// Contribution by Eric Ptak <trouch@trouch.com>
int
gpio_function(int gpio)
{
    int offset = OFFSET_FSEL + (gpio/10);
    int shift = (gpio%10)*3;
    int value = *(gpio_map+offset);
    value >>= shift;
    value &= 7;
    return value;
}

// Sets a GPIO output to 1 or 0
void
output_gpio(int gpio, int value)
{
    int offset;
    if (value) // value == HIGH
        offset = OFFSET_SET + (gpio / 32);
    else       // value == LOW
        offset = OFFSET_CLR + (gpio / 32);
    *(gpio_map+offset) = 1 << gpio % 32;
}

// Returns the value of a GPIO input (1 or 0)
int
input_gpio(int gpio)
{
   int offset, value, mask;
   offset = OFFSET_PINLEVEL + (gpio/32);
   mask = (1 << gpio%32);
   value = *(gpio_map+offset) & mask;
   return value;
}

void
cleanup(void)
{
    // fixme - set all gpios back to input
    munmap((caddr_t)gpio_map, BLOCK_SIZE);
}
