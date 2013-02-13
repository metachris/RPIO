"""
This script detects a Raspberry Pi's model and manufacturer based on the
revision number in /proc/cpuinfo.

Data source: http://www.raspberrypi.org/phpBB3/viewtopic.php?f=63&t=32733
"""
import re

model_data = {
    '0002': ('Model B Revision 1.0', '?'),
    '0003': ('Model B Revision 1.0 + Fuses mod and D14 removed', '?'),
    '0004': ('Model B Revision 2.0 256MB', 'Sony'),
    '0005': ('Model B Revision 2.0 256MB', 'Qisda'),
    '0006': ('Model B Revision 2.0 256MB', 'Egoman'),
    '0007': ('Model A Revision 2.0 256MB', 'Egoman'),
    '0008': ('Model A Revision 2.0 256MB', 'Sony'),
    '0009': ('Model A Revision 2.0 256MB', 'Qisda'),
    '000d': ('Model B Revision 2.0 512MB', 'Egoman'),
    '000e': ('Model B Revision 2.0 512MB', 'Sony'),
    '000f': ('Model B Revision 2.0 512MB', 'Qisda')
}

# Read cpuinfo to get the revision data
with open("/proc/cpuinfo") as f:
    cpuinfo = f.read()

# Find the revision with a regular expression
revision = re.search(r"(?<=\nRevision)[ |:|\t]*\w+", cpuinfo) \
        .group().strip(" :\t")

# Get model and maker information
model, maker = model_data[revision]

# Output results
print("Revision: %s" % revision)
print("Model: %s" % model)
print("Maker: %s" % maker)
