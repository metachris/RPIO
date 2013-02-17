"""
This script detects a Raspberry Pi's model, manufacturer and mb ram, based
on the cpu revision number. Data source:
http://www.raspberrypi.org/phpBB3/viewtopic.php?f=63&t=32733

You can instantiate the ModelInfo class either with a parameter `rev_hex`
(eg. `m = ModelInfo("000f")`), or without a parameter
(eg. `m = ModelInfo()`) in which case it will try to detect it via
`/proc/cpuinfo`. Accessible attributes:

    class ModelInfo:
        model = ''     # 'A' or 'B'
        revision = ''  # '1.0' or '2.0'
        ram_mb = 0     # integer value representing ram in mb
        maker = ''     # manufacturer (eg. 'Qisda')
        info = ''      # additional info (eg. 'D14' removed)

Author: Chris Hager <chris@linuxuser.at>
License: MIT
URL: https://github.com/metachris/raspberrypi-utils
"""
import re

model_data = {
    '0002': ('B', '1.0', 256, '?', ''),
    '0003': ('B', '1.0', 256, '?', 'Fuses mod and D14 removed'),
    '0004': ('B', '2.0', 256, 'Sony', ''),
    '0005': ('B', '2.0', 256, 'Qisda', ''),
    '0006': ('B', '2.0', 256, 'Egoman', ''),
    '0007': ('A', '2.0', 256, 'Egoman', ''),
    '0008': ('A', '2.0', 256, 'Sony', ''),
    '0009': ('A', '2.0', 256, 'Qisda', ''),
    '000d': ('B', '2.0', 512, 'Egoman', ''),
    '000e': ('B', '2.0', 512, 'Sony', ''),
    '000f': ('B', '2.0', 512, 'Qisda', '')
}


class ModelInfo(object):
    """
    You can instantiate ModelInfo either with a parameter `rev_hex`
    (eg. `m = ModelInfo("000f")`), or without a parameter
    (eg. `m = ModelInfo()`) in which case it will try to detect it via
    `/proc/cpuinfo`
    """
    model = ''
    revision = ''
    ram_mb = 0
    maker = ''
    info = ''

    def __init__(self, rev_hex=None):
        if not rev_hex:
            with open("/proc/cpuinfo") as f:
                cpuinfo = f.read()
            rev_hex = re.search(r"(?<=\nRevision)[ |:|\t]*\w+", cpuinfo) \
                    .group().strip(" :\t")

        self.revision_hex = rev_hex
        self.model, self.revision, self.ram_mb, self.maker, self.info = \
                model_data[rev_hex]

    def __repr__(self):
        s = "%s: Model %s, Revision %s, RAM: %s MB, Maker: %s%s" % ( \
                self.revision_hex, self.model, self.revision, self.ram_mb, \
                self.maker, ", %s" % self.info if self.info else "")
        return s


if __name__ == "__main__":
    m = ModelInfo()
    print(m)
