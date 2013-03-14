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
 */
#include <stdio.h>
#include <string.h>
#include "cpuinfo.h"

// Writes the hex revision str into the argument and returns:
//   2  (raspberry with revision 2 pin setup)
//   1  (raspberry with revision 1 pin setup)
//   0  (not a raspberry pi)
//   -1 (could not open /proc/cpuinfo)
//
// revision_hex will be four characters revision id (eg. '0004'),
// the over-voltage header, if present, is removed (since it is
// not consistently present on all overclocked boards).
int 
get_cpuinfo_revision(char *revision_hex)
{
    FILE *fp;
    char buffer[1024];
    char hardware[1024];
    int  rpi_found = 0;

    if ((fp = fopen("/proc/cpuinfo", "r")) == NULL)
        return -1;

    while(!feof(fp)) {
        fgets(buffer, sizeof(buffer) , fp);
        sscanf(buffer, "Hardware	: %s", hardware);
        if (strcmp(hardware, "BCM2708") == 0)
            rpi_found = 1;
        sscanf(buffer, "Revision	: %s", revision_hex);
    }
    fclose(fp);

    if (!rpi_found) {
        revision_hex = NULL;
        return 0;
    }

    // If over-voltage is present, remove it
    char* pos = strstr(revision_hex, "1000");
    if (pos && pos - revision_hex == 0 && strlen(revision_hex) > 5) {
        strcpy(revision_hex, revision_hex+(strlen(revision_hex) - 4));
    }

    // Returns revision
    if ((strcmp(revision_hex, "0002") == 0) ||
        (strcmp(revision_hex, "0003") == 0)) {
        return 1;
    } else {
        // assume rev 2 (0004 0005 0006 ...)
        return 2;
    }

    return -1;
}
