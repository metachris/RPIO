#!/bin/bash
#
# Very simple SD card backup script. Puts the content of the boot and root
# partitions into .tar files. Only works on Linux (not OSX) because of the
# filesystem types.
#
# Partition recognition:
# - if mounted: filesystem type ('vfat' and 'ext4')
# - if unmounted: partition type id ('c' and '83')
#
# Example partitions (if SD card is /dev/sdb):
#
#    Device Boot      Start         End      Blocks   Id  System
# /dev/sdb1               1        3201      102424    c  W95 FAT32 (LBA)
# /dev/sdb2            3202        7298      131104   82  Linux swap / Solaris
# /dev/sdb3            7299      242560     7528384   83  Linux
#
# To restore a backup, create the partitions and the filesystems, then
# simply extract the backup .tar files.
#
# Author: Chris Hager <chris@linuxuser.at>
# License: MIT (see /LICENSE.txt)
# URL: https://github.com/metachris/raspberrypi-utils

# Change this to your needs
BACKUPDIR="/tmp/raspberry-backup"

# Only change these if you know what you are doing
DEVICE_DEFAULT="/dev/sdb"
MOUNTPOINT="/mnt/rpi_sdcard"
DATESTR=`date +%Y-%m-%d_%H:%M`
BACKUPDIR="${BACKUPDIR}/backup_${DATESTR}"
CMD_TAR="tar -pcf"

function backup {
    # Perform a backup of the boot and root partition
    # usage: `backup <boot_mntpoint> <root_mntpoint>`
    mkdir -p $BACKUPDIR

    echo "Backing up 'boot'. This will take a moment..."
    cd $1 && $CMD_TAR "${BACKUPDIR}/boot.tar" *

    echo "Backing up 'root'. This will take a while..."
    cd $2 && $CMD_TAR "${BACKUPDIR}/root.tar" *
}

function search_mounts {
    # Test for mounted partitions
    # usage: `search_mounts <device>` (eg. `search_mounts /dev/sdb`)
    dir_boot=`mount | grep "^$1" | grep "type vfat" | awk '{ print $3 }'`
    dev_boot=`mount | grep "^$1" | grep "type vfat" | awk '{ print $1 }'`
    dir_root=`mount | grep "^$1" | grep "type ext4" | awk '{ print $3 }'`
    dev_root=`mount | grep "^$1" | grep "type ext4" | awk '{ print $1 }'`

    if [ -n "$dir_boot" ] && [ -n "$dir_root" ]; then
        echo "- already mounted linux partitions found"
        echo "- boot: $dev_boot on $dir_boot"
        echo "- root: $dev_root on $dir_root"
        echo
        echo -n "Use this as backup source?' [Y/n]? "
        read go_ahead
        if [ "$go_ahead" == "" ] || [ "$go_ahead" == "y" ] || [ "$go_ahead" == "Y" ]; then
            echo
            echo "Starting new backup with source boot=$dev_boot, root=$dev_root"
            backup $dir_boot $dir_root
            exit 0
        else
            SKIPDEVICE="1"
        fi
    else
        echo "- no mounted linux partitions found on $1"
    fi
}

function mountbackup {
    # mount > backup > unmount
    # usage: `mountbackup <dev_boot> <dev_root>`
    dev_boot = $1
    dev_root = $2

    dir_boot="${MOUNTPOINT}/boot"
    dir_root="${MOUNTPOINT}/root"

    mkdir -p $dir_boot
    mkdir -p $dir_root

    echo "- mounting 'boot' ($dev_boot)"
    mount $dev_boot $dir_boot

    echo "- mounting 'root' ($dev_root)"
    mount $dev_root $dir_root

    echo
    echo "Starting new backup with source boot=$dev_boot, root=$dev_root"
    backup $dir_boot $dir_root

    echo "- unmounting..."
    umount $dir_boot
    umount $dir_root
}

function search_device {
    # Search device for unmounted boot/root partitions
    # usage: `search_device <device>` (eg. `search_device /dev/sdb`)

    # 1. Search for boot partition: type 'c' (W95 FAT32 (LBA))
    dev_boot=`fdisk -l $1 | grep "^/dev" | awk '{ print $1" "$5 }' | grep " c" | awk '{ print $1 }'`

    # 2. Search for root partition: type '83' (Linux)
    dev_root=`fdisk -l $1 | grep "^/dev" | awk '{ print $1" "$5 }' | grep " 83" | awk '{ print $1 }'`

    if [ -n "$dev_boot" ] && [ -n "$dev_root" ]; then
        echo "- unmounted linux partitions found"
        echo "- boot: $dev_boot"
        echo "- root: $dev_root"
        echo
        echo -n "Use this as backup source?' [Y/n]? "
        read go_ahead
        if [ "$go_ahead" == "" ] || [ "$go_ahead" == "y" ] || [ "$go_ahead" == "Y" ]; then
            mountbackup $dev_boot $dev_root
            exit 0
        fi
    else
        echo "- no boot/root partitions found"
    fi
}

function _search {
    # Try to find boot/root partitions on this device (mounted or unmounted)
    # usage: `_search <device>` (eg. `_search /dev/sdb`)
    echo "Checking '$1'..."
    SKIPDEVICE=""
    search_mounts $1

    # If device was found but user wants another source, skip search_device.
    if [ "$SKIPDEVICE" == "" ]; then
        search_device $1
    fi
    echo
}

function ask_device {
    # Ask user for a device
    echo -n "Please enter device (eg. '/dev/sdc'): "
    read DEVICE_CUSTOM
}

# Startup Checks
unamestr=`uname`
if [ "$unamestr" != "Linux" ]; then
  echo "Error: Script only work on Linux"
  exit 1
fi

if [ $EUID -ne 0 ]; then
  echo "Error: Script needs to run as root"
  exit 2
fi

# Check default device
_search $DEVICE_DEFAULT

# Nothing found there; ask user for device
ask_device
_search $DEVICE_CUSTOM
