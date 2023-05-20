#!/usr/bin/env python3

import os
import re
import shutil
import sys

from typing import Optional
from pprint import pprint as _pprint
from dataclasses import dataclass, field


def twidth():
    w = os.environ.get('WIDTH', None)
    if w:
        return int(w)
    t = os.get_terminal_size(0)
    return t.columns


def pprint(*args, **kw):
    kw['width'] = twidth()
    kw['compact'] = False
    return _pprint(*args, **kw)


def p(d, i=0):
    if isinstance(d, dict):
        if not d:
            print('{}', end='')
            return
        print('{', end='\n')
        for k in sorted(d):
            if isinstance(k, tuple):
                v = '('+hex(k[0])+', '+hex(k[1])+')'
            else:
                v = repr(k)

            print((i+1)*' ', v, ':', end=' ')
            p(d[k], i+1)
            print(',', end='\n')
        print(i*' ', '}', end='')
    else:
        print(repr(d), end='')


F = 0xffffffffffff
M = len('39c000000000')


def pmem(region, i=0):
    # '|',    == 1+1
    # p1,     == 5+1
    # hstart, == M+1
    # hend,   == M+1
    # p2,     == 0+1
    # '|',    == 1+1
    # hsize,  == M+1
    # '|',    == 1+1
    # p1,     == 5+1
    S = 1+1 + 5+1 + M+1 + M+1 + 0+1 + 1+1 + M+1 + 1+1 + 5+1 + 1

    def print_header():
        print('|', lpad('Start', ' ', M), lpad('End', ' ', M), '      ', '|', lpad('Size', ' ', M), '|', "Device")
    if i == 0:
        print_header()

    rend = [F]

    for (istart, iend), d in region.items():
        if (istart, iend) == (0, 0):
            continue

        isize = iend-istart+1

        hstart = lpad(hex(istart)[2:], '0', M)
        hend   = lpad(hex(iend)[2:], '0', M)
        hsize  = lpad(hex(isize)[2:], ' ', M)

        info = d.get((0, 0), [])

        if 'DMI2' in repr(info) or 'Root Port' in repr(info):
            print()
            print()
            print_header()
            rend[0] = iend+1
        elif istart >= rend[0]:
            print()
            print()
            print_header()
            rend[0] = F

        p1 = ' '*i
        p2 = ' '*(5-i)

        sinfo = " && ".join(info)[:twidth()-S]

        print('|', p1, hstart, hend, p2, '|', hsize, '|', p1, sinfo) #" && ".join(info))

        if len(d) == 1:
            continue

        pmem(d, i+1)


def lpad(s, n, l):
    while len(s) < l:
        s = n+s
    return s


def parents(start, end, regions):
    """
    >>> regions = {}
    >>> a = (0, 1000)
    >>> b = (2000, 3000)
    >>> 
    >>> parents(*a, regions)
    {}
    >>> parents(*b, regions)
    {}
    >>> list(regions.keys())
    [(0, 1000), (2000, 3000)]
    >>> parents(100, 200, regions)
    {}
    >>> list(regions.keys())
    [(0, 1000), (2000, 3000)]
    >>> list(sorted(regions[a].keys()))
    [(100, 200)]
    >>> parents(50, 75, regions)
    {}
    >>> list(sorted(regions[a].keys()))
    [(50, 75), (100, 200)]
    >>> parents(2000, 2100, regions)
    {}
    >>> list(regions.keys())
    [(0, 1000), (2000, 3000)]
    >>> list(sorted(regions[b].keys()))
    [(2000, 2100)]
    >>> parents(2000, 2001, regions)
    {}
    >>> list(sorted(regions[b].keys()))
    [(2000, 2100)]
    >>> parents(200, 300, regions)
    {}
    >>> parents(100, 150, regions)
    {}
    >>> p(regions)
    {
      (0x0, 0x3e8) : {
       (0x32, 0x4b) : {},
       (0x64, 0xc8) : {
        (0x64, 0x96) : {},
       },
       (0xc8, 0x12c) : {},
      },
      (0x7d0, 0xbb8) : {
       (0x7d0, 0x834) : {
        (0x7d0, 0x7d1) : {},
       },
      },
     }
    """
    assert end >= start, (start, end)

    if (start, end) in regions:
        return regions[(start, end)]

    for (istart, iend) in regions.keys():
        if start < istart:
            continue
        if start >= iend:
            continue

        assert end <= iend, ((hex(start), hex(end)), (hex(istart), hex(iend)))

        return parents(start, end, regions[(istart, iend)])

    if (start, end) not in regions:
        regions[(start, end)] = {}
    return regions[(start, end)]


@dataclass
class Device:
    address: str
    description: str
    subsystem: str
    control: str
    status: str
    latency: str
    kernel_driver: str


class HexInt(int):
    def __repr__(self):
        return hex(self)
    def __str__(self):
        return hex(self)


@dataclass(eq=True, order=True, unsafe_hash=True)
class Region:
    rtype: str
    region: int = field(compare=False)
    address: HexInt
    size: int

    bits: int
    disabled: bool = field(kw_only=True, default=False)
    virtual: bool = field(kw_only=True, default=False)
    prefetchable: Optional[bool] = field(kw_only=True, default=None)

    @property
    def start(self):
        return self.address

    @property
    def end(self):
        assert self.size is not None, self
        return HexInt(self.address + self.size - 1)

    @property
    def range(self):
        return self.address, self.end


@dataclass(eq=True, order=True, unsafe_hash=True)
class BridgeRegion:
    prefetchable: bool
    type: str

    start: HexInt
    end: HexInt
    size: int

    disabled: bool
    bits: int

    @property
    def range(self):
        return self.start, self.end

    @property
    def csize(self):
        return self.end - self.start


@dataclass(eq=True, order=True, unsafe_hash=True)
class CapabilityVendor:
    id: int
    rev: int
    len: int


@dataclass(eq=True, order=True, unsafe_hash=True)
class Capability:
    id: int
    version: int

    name: Optional[str]
    vendor: Optional[CapabilityVendor] = field(kw_only=True, default=None)
    types: Optional[tuple[str]] = field(kw_only=True, default=None)

    properties: list = field(hash=False)
    regions: Optional[list[Region]] = field(hash=False, default_factory=list)


def convert_size_to_bytes(size: str) -> int:
    """
    Converts the size string to bytes.

    Args:
        size (str): The size string, e.g., '8K', '256', '512M', etc.

    Returns:
        int: The size in bytes.

    >>> convert_size_to_bytes('8K')
    8192

    >>> convert_size_to_bytes('256')
    256

    >>> convert_size_to_bytes('512M')
    536870912

    >>> convert_size_to_bytes('2G')
    2147483648

    >>> convert_size_to_bytes('10')
    10

    >>> convert_size_to_bytes('1T')
    1099511627776

    """

    units = {
        'K': 1024,
        'M': 1024 * 1024,
        'G': 1024 * 1024 * 1024,
        'T': 1024 * 1024 * 1024 * 1024
    }

    size = size.upper()
    if size[-1] in units:
        return int(size[:-1]) * units[size[-1]]
    else:
        return int(size)


def parse_region(line: str) -> Region:
    """
    Extracts region information from the given line and returns a Region object.

    Args:
        line (str): The input line containing region information.

    Returns:
        Region: A Region object representing the extracted region information.

    >>> p = parse_region("Region 0: Memory at 90334000 (32-bit, non-prefetchable) [size=8K]")
    >>> p
    Region(rtype='Memory', region=0, address=0x90334000, size=8192, bits=32, disabled=False, virtual=False, prefetchable=False)
    >>> p.end
    0x90335fff
    >>> p.range
    (0x90334000, 0x90335fff)

    >>> parse_region("Region 1: Memory at 90339000 (32-bit, non-prefetchable) [size=256]")
    Region(rtype='Memory', region=1, address=0x90339000, size=256, bits=32, disabled=False, virtual=False, prefetchable=False)

    >>> parse_region("Region 2: I/O ports at 3050 [size=8]")
    Region(rtype='I/O ports', region=2, address=0x3050, size=8, bits=-1, disabled=False, virtual=False, prefetchable=None)

    >>> parse_region("Region 3: I/O ports at 3040 [size=4]")
    Region(rtype='I/O ports', region=3, address=0x3040, size=4, bits=-1, disabled=False, virtual=False, prefetchable=None)

    >>> parse_region("Region 4: I/O ports at 3000 [size=32]")
    Region(rtype='I/O ports', region=4, address=0x3000, size=32, bits=-1, disabled=False, virtual=False, prefetchable=None)

    >>> parse_region("Region 4: I/O ports at efa0 [size=32]")
    Region(rtype='I/O ports', region=4, address=0xefa0, size=32, bits=-1, disabled=False, virtual=False, prefetchable=None)

    >>> parse_region("Region 5: Memory at 90200000 (32-bit, non-prefetchable) [size=512K]")
    Region(rtype='Memory', region=5, address=0x90200000, size=524288, bits=32, disabled=False, virtual=False, prefetchable=False)

    >>> parse_region('Region 0: Memory at f9000000 (64-bit prefetchable) [size=8M]')
    Region(rtype='Memory', region=0, address=0xf9000000, size=8388608, bits=64, disabled=False, virtual=False, prefetchable=True)

    >>> parse_region('Region 3: Memory at fb800000 (64-bit prefetchable) [size=32K]')
    Region(rtype='Memory', region=3, address=0xfb800000, size=32768, bits=64, disabled=False, virtual=False, prefetchable=True)

    >>> p = parse_region('Region 0: Memory at f0000000 (32-bit, non-prefetchable) [disabled] [size=16M]')
    >>> p
    Region(rtype='Memory', region=0, address=0xf0000000, size=16777216, bits=32, disabled=True, virtual=False, prefetchable=False)
    >>> p.end
    0xf0ffffff

    >>> parse_region('Region 0: Memory at 4017001000 (64-bit non-prefetchable) [virtual] [size=4K]')
    Region(rtype='Memory', region=0, address=0x4017001000, size=4096, bits=64, disabled=False, virtual=True, prefetchable=False)

    >>> parse_region('Region 0: Memory at 0000004010000000 (64-bit non-prefetchable)')
    Region(rtype='Memory', region=0, address=0x4010000000, size=None, bits=64, disabled=False, virtual=False, prefetchable=False)

    >>> parse_region('Region 0: Memory at <ignored> (low-1M, prefetchable) [disabled]')
    Region(rtype='Memory', region=0, address=-1, size=None, bits=-1, disabled=True, virtual=False, prefetchable=True)

    """
    pattern = re.compile(
        r"Region (?P<region>\d+): (Memory at (?P<memory_address>([0-9a-fA-F]+)|(<ignored>)) \((low-1M,?\s*)?(\d+-bit,?\s*)?(non-)?prefetchable\)|I/O ports at (?P<io_address>[0-9a-fA-F]+))(\s*\[virtual])?(\s*\[disabled])?\s*(\[size=(?P<size>\d+[KMG]?)])?"
    )

    m = pattern.match(line)
    if not m:
        raise ValueError("Invalid line format: "+repr(line))

    region = int(m.group("region"))
    saddress = m.group("io_address") or m.group("memory_address")
    if saddress != '<ignored>':
        address = HexInt(saddress, 16)
    else:
        address = -1

    if 'Memory at' in line:
        rtype='Memory'
    elif 'I/O ports at' in line:
        rtype='I/O ports'
    else:
        rtype=None

    if '32-bit' in line:
        bits=32
    elif '64-bit' in line:
        bits=64
    else:
        bits=-1

    if 'non-prefetchable' in line:
        prefetchable=False
    elif 'prefetchable' in line:
        prefetchable=True
    else:
        prefetchable=None

    if '[disabled]' in line:
        disabled=True
    else:
        disabled=False

    if '[virtual]' in line:
        virtual=True
    else:
        virtual=False

    size = m.group("size")
    if size:
        size = convert_size_to_bytes(size)

    region_info = Region(
        rtype,
        region, address, size, bits,
        prefetchable=prefetchable,
        disabled=disabled,
        virtual=virtual)
    return region_info


RE_BEHIND = re.compile(
    "^(?P<prefetch>Prefetchable\s)?(?P<mtype>.*)\sbehind\sbridge:\s*"
    "(?P<mstart>[0-9a-fA-F]+)(?P<mend>-[0-9a-fA-F]+)\s*"
    "(\[(?P<disabled>disabled)\])?\s*"
    "(\[size=(?P<size>[0-9]*.)\])?\s*"
    "(\[(?P<bits>[0-9][0-9])-bit\])?\s*"
)

def parse_behind_bridge(s):
    """
    >>> parse_behind_bridge("I/O behind bridge: 0000f000-00000fff [disabled]")
    BridgeRegion(prefetchable=True, type='i/o', start=0xf000, end=0xfff, size=None, disabled=True, bits=None)

    >>> parse_behind_bridge("I/O behind bridge: f000-0fff [disabled] [16-bit]")
    BridgeRegion(prefetchable=True, type='i/o', start=0xf000, end=0xfff, size=None, disabled=True, bits=16)

    >>> parse_behind_bridge("Memory behind bridge: d0900000-d09fffff [size=1M] [32-bit]")
    BridgeRegion(prefetchable=True, type='memory', start=0xd0900000, end=0xd09fffff, size=1048576, disabled=False, bits=32)

    >>> parse_behind_bridge("Prefetchable memory behind bridge: 00000000fff00000-00000000000fffff [disabled] [64-bit]")
    BridgeRegion(prefetchable=False, type='memory', start=0xfff00000, end=0xfffff, size=None, disabled=True, bits=64)

    >>> parse_behind_bridge("Memory behind bridge: b3000000-b40fffff [size=17M] [32-bit]")
    BridgeRegion(prefetchable=True, type='memory', start=0xb3000000, end=0xb40fffff, size=17825792, disabled=False, bits=32)

    >>> parse_behind_bridge("Prefetchable memory behind bridge: a0000000-b20fffff [size=289M] [32-bit]")
    BridgeRegion(prefetchable=False, type='memory', start=0xa0000000, end=0xb20fffff, size=303038464, disabled=False, bits=32)

    >>> parse_behind_bridge("Memory behind bridge: b8000000-d01fffff [size=386M] [32-bit]")
    BridgeRegion(prefetchable=True, type='memory', start=0xb8000000, end=0xd01fffff, size=404750336, disabled=False, bits=32)

    >>> parse_behind_bridge("Prefetchable memory behind bridge: 103fc0000000-103ffbffffff [size=960M] [32-bit]")
    BridgeRegion(prefetchable=False, type='memory', start=0x103fc0000000, end=0x103ffbffffff, size=1006632960, disabled=False, bits=32)

    >>> parse_behind_bridge("Memory behind bridge: f0000000-f10fffff [size=17M] [32-bit]")
    BridgeRegion(prefetchable=True, type='memory', start=0xf0000000, end=0xf10fffff, size=17825792, disabled=False, bits=32)

    >>> parse_behind_bridge("Prefetchable memory behind bridge: f9000000-fbafffff [size=43M] [32-bit]")
    BridgeRegion(prefetchable=False, type='memory', start=0xf9000000, end=0xfbafffff, size=45088768, disabled=False, bits=32)

    """
    m = RE_BEHIND.search(s)

    prefetchable = m.group('prefetch') is None
    mtype = m.group('mtype').lower()

    mstart = HexInt(m.group('mstart'), 16)
    mend = HexInt(m.group('mend')[1:], 16)

    disabled = m.group('disabled') is not None

    msize = m.group('size')
    if msize:
        msize = convert_size_to_bytes(msize)

    bits = m.group('bits')
    try:
        bits = int(bits)
    except TypeError:
        pass

    return BridgeRegion(
            prefetchable=prefetchable,
            type=mtype,
            start=mstart, end=mend, size=msize,
            disabled=disabled,
            bits=bits,
        )


RE_COLON_SPACE = re.compile('^\t*[A-Za-z0-9 /]+: ')
RE_COLON_TAB   = re.compile('^\t*[A-Za-z0-9 /]+:\t')
RE_COLON_SPACE_CONT = re.compile('^\t+ ')
RE_COLON_TAB_CONT   = re.compile('^\t+')


def _fixup(s):
    # Convert the following into "colon-tab" setup.
    s = s.replace('Capabilities: ', 'Capabilities:\t')
    s = s.replace('BridgeCtl: ', 'BridgeCtl:\t')
    s = s.replace('Read-only fields:', 'Read only fields:\t')

    # Convert 'Expansion ROM at d0800000 [disabled] [size=256K]`
    # to      'Expansion ROM: d0800000 [disabled] [size=256K]`
    s = s.replace('Expansion ROM at ', 'Expansion ROM: ')
    # Convert 'Region 0: Memory at 90330000 (32-bit, non-prefetchable) [disabled] [size=16K]'
    # to      'Region 0: Memory at 90330000 (32-bit non-prefetchable) [disabled] [size=16K]'
    s = s.replace('bit, ', 'bit ')
    # Convert 'FRS- LN System CLS Not Supported, TPHComp+ ExtTPHComp- ARIFwd+'
    # to      'FRS- LN System CLS Not Supported, TPHComp+ ExtTPHComp- ARIFwd+'
    s = s.replace('LN System CLS', 'LN-System-CLS')
	# Convert `LnkCtl: ASPM Disabled; RCB 64 bytes, Disabled- CommClk+`
	# to      `LnkCtl: ASPM Disabled, RCB 64 bytes, Disabled- CommClk+`
    s = s.replace('; ', ', ')
    # Convert 'Exit Latency L0s <1us, L1 <4us'
    # to      'Exit Latency L0s <1us L1 <4us'
    s = s.replace(', L1', ' L1')

    # Convert: `Flags: PMEClk- DSI- D1- D2- AuxCurrent=0mA PME(D0+,D1-,D2-,D3hot+,D3cold+)`
    # to       `Flags: PMEClk- DSI- D1- D2- AuxCurrent=0mA, PME: D0+ D1- D2- D3hot+ D3cold+,`
    def _fix_pme(match_obj):
        f = match_obj.group(1).replace(",", " ")
        return f', PME: {f}, '
    s = re.sub(r' *PME\(([^\)]+)\) *', _fix_pme, s)

    # Convert `Compliance Preset/De-emphasis: -6dB de-emphasis, 0dB preshoot`
    # to      `Compliance Preset/De-emphasis: -6dB de-emphasis 0dB preshoot`
    s = s.replace('dB de-emphasis, ', 'dB de-emphasis ')

    # Convert ` CrosslinkRes: unsupported`
    # to      ` CrosslinkRes=unsupported`
    s = s.replace(' CrosslinkRes: unsupported', ' CrosslinkRes=unsupported')

    # Convert ' Interrupt Message Number: '
    # to      ' Interrupt-Message-Number='
    s = s.replace(' Interrupt Message Number: ', ' Interrupt-Message-Number=')

    # Convert 'L1SubCtl2:\n'
    # to      'L1SubCtl2: Unsupported\n'
    s = s.replace('L1SubCtl2:\n', 'L1SubCtl2: \n')

    return s


def undo_multiline(x):
    o = []
    mode = None
    while x:
        l = x.pop(0)
        if mode == 'colon-space' and RE_COLON_SPACE_CONT.search(l):
            o[-1] += ', ' + l.strip()
        elif RE_COLON_SPACE.search(l):
            o.append(l)
            mode = 'colon-space'
        elif RE_COLON_TAB.search(l):
            a, b = l.split(':\t', 1)
            o.append(a+": "+b)
            mode = 'colon-tab'
        elif mode == 'colon-tab' and RE_COLON_TAB_CONT.search(l):
            o[-1] += ', ' + l.strip()
        else:
            assert False, (l, mode, o[-1])

    x = o
    o = [None]
    while x:
        l = x.pop(0)

        if l.startswith('\t'):
            if not isinstance(o[-1], list):
                o[-1] = [o[-1], l[1:]]
            else:
                o[-1].append(l[1:])

        if isinstance(o[-1], list) and (not l.startswith('\t') or not x):
            o[-1] = undo_multiline(o[-1])

        if not l.startswith('\t'):
            o.append(l)

    return o[1:]


def group_device_lines(lines):
    devices = []
    current_device = None
    while lines:
        line = lines.pop(0)

        if not line.strip():
            if current_device:
                current_device[-1] = undo_multiline(current_device[-1])
                devices.append(current_device)
            current_device = None
            continue

        if not current_device:
            assert line[0] != '\t', repr(line)
            current_device = [line, []]
        else:
            assert line[0] == '\t', repr(line)
            current_device[-1].append(line[1:])
        continue

    return devices


FLAGS = {
    'Control': None,
    'Status': None,
    'BridgeCtl': None,
    'Secondary status': None,
}



def parse_flags(l):
    """
    >>> parse_flags('I/O+ Mem+ BusMaster+ SpecCycle- MemWINV-')
    {'I/O': True, 'Mem': True, 'BusMaster': True, 'SpecCycle': False, 'MemWINV': False}

    >>> parse_flags(['I/O+ Mem+ BusMaster+', 'SpecCycle-'])
    {'I/O': True, 'Mem': True, 'BusMaster': True, 'SpecCycle': False}

    """
    if isinstance(l, list):
        l = ' '.join(l)

    assert ', ' not in l, l
    assert ': ' not in l, l

	# `LnkCap:	Port #9, Speed 8GT/s, Width x1, ASPM L0s L1, Exit Latency L0s <1us, L1 <4us`
    if 'ASPM ' in l:
        b = l.split(' ')
        assert b[0] == 'ASPM', (b, l)
        l = 'ASPM='+','.join(b[1:])

	# `10BitTagComp- 10BitTagReq- OBFF Not Supported, ExtFmt- EETLPPrefix-`
	# `EmergencyPowerReduction Not Supported, EmergencyPowerReductionInit-`
    l = l.replace(' Not Supported','=Unsupported')
	# `LnkCap:	Port #1, Speed 8GT/s, Width x8, ASPM not supported`
    l = l.replace(' not supported','=Unsupported')
	# `DevCtl2: Completion Timeout: 50us to 50ms, TimeoutDis- LTR- 10BitTagReq- OBFF Disabled,`
	# `LnkCtl:	ASPM Disabled; RCB 64 bytes, Disabled- CommClk+`
    l = l.replace(' Disabled', '=Disabled')
    # `10BitTagComp- 10BitTagReq- OBFF Via message, ExtFmt- EETLPPrefix-`
    l = l.replace(' Via ','=Via-')
	# `RootSta: PME ReqID 0000, PMEStatus- PMEPending-`
    l = l.replace('PME ReqID ','PME-ReqID=')
	# `ExtTag- AttnBtn- AttnInd- PwrInd- RBE+ FLReset+ SlotPowerLimit 0W`
    l = l.replace('SlotPowerLimit ', 'SlotPowerLimit=')
    # `Status: D0 NoSoftRst+ PME-Enable- DSel=0 DScale=0 PME-`
    l = l.replace('D0 ', 'D0+ ')
	# `Status: D3 NoSoftRst- PME-Enable+ DSel=0 DScale=0 PME-`
    l = l.replace('D3 ', 'D3+ ')
    # `FirstFatal- NonFatalMsg- FatalMsg- IntMsg 0`
    l = l.replace('IntMsg ', 'IntMsg=')
    l = l.replace('INT Msg #', 'IntMsg=')
    l = l.replace('RP PIO Log ', 'RP-PIO-Log=')
    l = l.replace('RP PIO ErrPtr:', 'RP-PIO-ErrPtr=')
    l = l.replace('Trigger:', 'Trigger=')
    l = l.replace('TriggerExt:', 'TriggerExt=')
    l = l.replace('Reason:', 'Reason=')
    # ``
    l = l.replace('Slot #', 'Slot=#')
    l = l.replace('PowerLimit ', 'PowerLimit=')

    flags = {}
    for f in l.split():
        if '=' in f:
            name, value = f.split('=')
            flags[name] = value
            continue

        assert f[-1] in '-+', (f, l)
        name = f[:-1]
        value = {'-': False, '+': True}[f[-1]]
        assert name not in flags, (name, flags, l)
        flags[name] = value
    return flags


RE_CAPS = re.compile(r"Capabilities: \[([\da-fA-F]+)( v\d+)?\] (.*?)$")
RE_VENDOR = re.compile(r"Vendor Specific Information:\s*(ID=(?P<id>[\da-fA-F]+))?\s*(Rev=(?P<rev>\d+))?\s*Len=(?P<len>\w+) <\?>")


CAPS_FLAGS = {
    'SltCap':  None,

    'DpcCap': None,
    'DpcCtl': None,
    'DpcSta': None,

    'DevCap':  None, # Special cased
    'DevCtl':  None,
    'DevSta':  None,

    'DevCap2': None,
    'DevCtl2': None,
    'DevSta2': None,

    'LnkCap':  None, # Special cased
    'LnkCtl':  None, # Special cased
    'LnkSta':  None, # Special cased

    'LnkCap2': None,
    'LnkCtl2': None,
    'LnkSta2': None,

    'L1SubCap': None,
    'L1SubCtl1': None,
    'L1SubCtl2': None,

    'IOVCap':  None,
    'IOVCtl':  None,
    'IOVSta':  None,

    'ACSCap':  None,
    'ACSCtl':  None,
    'ACSSta':  None,

    'RootCmd': None,
    'RootCap': None,
    'RootCtl': None,
    'RootSta': None,

    'AERCap':  None,
    'AERCtl':  None,
    'AERSta':  None,

    'UECap':   None,
    'UECtl':   None,
    'UESta':   None,
    'UEMsk':   None,

    'CEMsk':   None,
    'CESta':   None,

    'UESvrt':  None,

    'Flags': None,
    'Status': None,

    'PRICtl': None,
    'PRISta': None,

    'PASIDCap': None,
    'PASIDCtl': None,

    # subsub-capacity flags
    'AtomicOpsCap': None,
    'AtomicOpsCtl': None,
    'AtomicOpsSta': None,

    'PME': None,

    # Capabilities: [220 v1] Secondary PCI Express
	#	LnkCtl3: LnkEquIntrruptEn- PerformEqu+
	#	LaneErrStat: 0
    'LnkCtl3': None,
}


def parse_vendor(s):
    mv = RE_VENDOR.match(s)
    assert mv, s

    vid = -1
    try:
        vid = int(mv.group('id'), 16)
    except TypeError:
        pass

    vrev = -1
    try:
        vrev = int(mv.group('rev'), 16)
    except TypeError:
        pass

    vlen = int(mv.group('len'), 16)

    return CapabilityVendor(id=vid, rev=vrev, len=vlen)


def parse_caps(p):
    """
    >>> parse_caps("Capabilities: [160 v1] Single Root I/O Virtualization (SR-IOV)")
    Capability(id=352, version=1, name='Single Root I/O Virtualization (SR-IOV)', vendor=None, types=None, properties=[], regions=[])

    >>> parse_caps("Capabilities: [40] Express (v2) Root Port (Slot-), MSI 00")
    Capability(id=64, version=-1, name='Unknown', vendor=None, types=['Express (v2) Root Port (Slot-)', 'MSI 00'], properties=[], regions=[])

    >>> parse_caps("Capabilities: [300 v1] Vendor Specific Information: ID=0008 Rev=0 Len=038 <?>")
    Capability(id=768, version=1, name='Unknown', vendor=CapabilityVendor(id=8, rev=0, len=56), types=None, properties=[], regions=[])

    >>> parse_caps("Capabilities: [1a0 v1] Transaction Processing Hints, Device specific mode supported, Steering table in TPH capability structure")
    Capability(id=416, version=1, name='Unknown', vendor=None, types=['Transaction Processing Hints', 'Device specific mode supported', 'Steering table in TPH capability structure'], properties=[], regions=[])

    >>> parse_caps("Capabilities: [e0] Vendor Specific Information: Len=1c <?>")
    Capability(id=224, version=-1, name='Unknown', vendor=CapabilityVendor(id=-1, rev=-1, len=28), types=None, properties=[], regions=[])

    >>> parse_caps('Capabilities: [40] Vendor Specific Information: Len=0c <?>')
    Capability(id=64, version=-1, name='Unknown', vendor=CapabilityVendor(id=-1, rev=-1, len=12), types=None, properties=[], regions=[])

    """
    assert p.startswith("Capabilities: "), p
    m = RE_CAPS.match(p)
    if not m:
        raise SyntaxError(p)
    (cap, v, name) = m.groups()
    if not v:
        v = -1
    else:
        assert v.startswith(' v'), (v, p)
        v = int(v[2:])

    vendor = None
    types = None
    if name.startswith('Vendor Specific Information:'):
        vendor = parse_vendor(name)
        name = 'Unknown'
    elif ', ' in name:
        types = name.split(', ')
        name = 'Unknown'

    return Capability(int(cap, 16), v, name, [], vendor=vendor, types=types)


def parse_lspci_output(output):
    output = _fixup(output)

    device_lines = group_device_lines(output.splitlines())
    devices = []
    for device, lines in device_lines:
        details = {}
        for l in lines:
            if isinstance(l, str) and l.startswith('Capabilities: '):
                l = [l]

            if isinstance(l, list):
                assert l[0].startswith('Capabilities: '), l[0]
                if 'Capabilities' not in details:
                    details['Capabilities'] = []
                cap = parse_caps(l[0])

                properties = {}
                for p in l[1:]:
                    if ': ' in p:
                        if p.startswith('Region '):
                            cap.regions.append(parse_region(p))
                            continue

                        key, value = p.split(': ', 1)

                        bits = value.split(', ')

                        subproperties = {}
                        def u(s, b):
                            for k, v in parse_flags(b).items():
                                assert k not in s, (k, v, s[k], b)
                                s[k] = v

                        for b in bits:
                            if ': ' in b:
                                skey, svalue = b.split(': ', 1)
                                if skey in CAPS_FLAGS:
                                    subproperties[skey] = {}
                                    u(subproperties[skey], svalue)
                                else:
                                    subproperties[skey] = svalue
                            elif key in ('DevCap', 'DevCtl',):
                                if b.startswith('MaxPayload '):
                                    assert b.endswith(' bytes'), (key, b, l)
                                    subproperties['MaxPayload'] = int(b[len('MaxPayload '):-len(' bytes')])
                                elif b.startswith('MaxReadReq '):
                                    assert b.endswith(' bytes'), (key, b, l)
                                    subproperties['MaxReadReq'] = int(b[len('MaxReadReq '):-len(' bytes')])
                                elif b.startswith('PhantFunc '):
                                    subproperties['PhantFunc'] = b[len('PhantFunc '):]
                                elif b.startswith('Latency L0s') or b.startswith('L1 '):
                                    subproperties[b] = None
                                else:
                                    u(subproperties, b)
                            elif key in ('LnkCap', 'LnkCtl', 'LnkSta'):
                                if b.startswith('Port #'):
                                    subproperties['Port #'] = int(b[len('Port #'):])
                                elif b.startswith('Speed '):
                                    subproperties['Speed'] = b[len('Speed '):]
                                elif b.startswith('Exit Latency '):
                                    subproperties['Exit Latency'] = b[len('Exit Latency '):]
                                elif b.startswith('Width '):
                                    subproperties['Width'] = b[len('Width '):]
                                elif b.startswith('RCB '):
                                    assert b.endswith(' bytes'), (key, b, l)
                                    subproperties['RCB'] = int(b[len('RCB '):-len(' bytes')])
                                else:
                                    u(subproperties, b)
                            elif key in CAPS_FLAGS:
                                u(subproperties, b)
                            else:
                                subproperties[b] = None

                        value = subproperties
                    properties[key] = value
                cap.properties = properties
                details['Capabilities'].append(cap)
                continue

            if l.startswith('Region '):
                if 'Regions' not in details:
                    details['Regions'] = []
                details['Regions'].append(parse_region(l))
                continue

            assert isinstance(l, str), l
            assert ': ' in l, l
            name, value = l.split(': ', 1)

            if name.endswith(' behind bridge'):
                value = parse_behind_bridge(l)
                if 'BridgeRegions' not in details:
                    details['BridgeRegions'] = []
                details['BridgeRegions'].append(value)

            elif ',' in value:
                value = [v.strip() for v in value.split(',')]

            if name in FLAGS:
                value = parse_flags(value)

            details[name] = value
        devices.append((device, details))
    return devices


def main(args):
    try:
        output = open('lspci.vvv').read()
    except FileNotFoundError:
        import subprocess
        output = subprocess.check_output(["lspci", "-vvv"], universal_newlines=True)

    devices = parse_lspci_output(output)

    regions = []
    enabled = []
    bridges = []
    for name, details in devices:
        print()
        print()
        print(name)
        pprint(details)
        for r in details.get('Regions', []):
            regions.append((r, name))
            if not r.disabled:
                enabled.append((r, name))
        for r in details.get('BridgeRegions', []):
            bridges.append((r, name))
            if not r.disabled:
                enabled.append((r, name))

    # 'I/O behind bridge': '0000f000-00000fff [disabled]',
    # 'Memory behind bridge': 'bc300000-bc3fffff [size=1M]',
    # 'Prefetchable memory behind bridge': '00000000fff00000-00000000000fffff [disabled]',

    print()
    print('='*twidth())

    print()
    print('Regions')
    print('-'*twidth())
    regions.sort()
    for r, d in regions:
        print(r, d.split(' ', 1)[0])
    print('-'*twidth())

    print()
    print('Bridge Regions')
    print('-'*twidth())
    bridges.sort()
    for r, d in bridges:
        print(r, d.split(' ', 1)[0])
    print('-'*twidth())
    print()

    print()
    print('Enabled Regions (device & bridge)')
    print('-'*twidth())
    enabled.sort(key=lambda x: (x[0].start, F-x[0].end, x[1]))
    for r, d in enabled:
        print(r.range, r.__class__.__name__[0], d)
    print('-'*twidth())

    tree = {}
    for r, n in enabled:
        d = parents(r.start, r.end, tree)
        if (0, 0) not in d:
            d[(0,0)] = []
        d[(0,0)].append(n)

    pmem(tree)
    print()
    print('='*twidth())
    print()

    return 0


if __name__ == "__main__":
    import doctest
    if doctest.testmod().failed > 0:
        sys.exit(1)
    sys.exit(main(sys.argv))
