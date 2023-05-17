#!/usr/bin/env python3

import os
import re
import shutil
import sys

from typing import Optional
from pprint import pprint as _pprint
from dataclasses import dataclass, field


def twidth():
    t = os.get_terminal_size(0)
    return t.columns

def pprint(*args, **kw):
    kw['width'] = twidth()
    kw['compact'] = False
    return _pprint(*args, **kw)


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
    region: int
    address: HexInt
    size: int


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


def parse_region(s):
    """

    >>> parse_region('Region 0: Memory at f9000000 (64-bit prefetchable) [size=8M]')

    >>> parse_region('Region 3: Memory at fb800000 (64-bit prefetchable) [size=32K]')

    >>> parse_region('Region 0: Memory at f0000000 (32-bit, non-prefetchable) [disabled] [size=16M]')

    """


def extract_region_info(line: str) -> Region:
    """
    Extracts region information from the given line and returns a Region object.

    Args:
        line (str): The input line containing region information.

    Returns:
        Region: A Region object representing the extracted region information.

    >>> extract_region_info("Region 0: Memory at 90334000 (32-bit, non-prefetchable) [size=8K]")
    Region(region=0, address=0x90334000, size=8192)

    >>> extract_region_info("Region 1: Memory at 90339000 (32-bit, non-prefetchable) [size=256]")
    Region(region=1, address=0x90339000, size=256)

    >>> extract_region_info("Region 2: I/O ports at 3050 [size=8]")
    Region(region=2, address=0x3050, size=8)

    >>> extract_region_info("Region 3: I/O ports at 3040 [size=4]")
    Region(region=3, address=0x3040, size=4)

    >>> extract_region_info("Region 4: I/O ports at 3000 [size=32]")
    Region(region=4, address=0x3000, size=32)

    >>> extract_region_info("Region 5: Memory at 90200000 (32-bit, non-prefetchable) [size=512K]")
    Region(region=5, address=0x90200000, size=524288)
    """
    pattern = re.compile(
        r"Region (?P<region>\d+): (Memory at (?P<memory_address>[0-9a-fA-F]+) \(\d+-bit, non-prefetchable\)|I/O ports at (?P<io_address>\d+)) \[size=(?P<size>\d+[KMG]?)]"
    )

    match = pattern.match(line)
    if not match:
        raise ValueError("Invalid line format")

    region = int(match.group("region"))
    address = HexInt(match.group("io_address") or match.group("memory_address"), 16)
    size = convert_size_to_bytes(match.group("size"))
    region_info = Region(region, address, size)
    return region_info


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
RE_VENDOR = re.compile(r"Vendor Specific Information: ID=(?P<id>[\da-fA-F]+) Rev=(?P<rev>\d+) Len=(?P<len>\w+) <\?>")


CAPS_FLAGS = {
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


def parse_caps(p):
    """
    >>> parse_caps("Capabilities: [160 v1] Single Root I/O Virtualization (SR-IOV)")
    Capability(id=352, version=1, name='Single Root I/O Virtualization (SR-IOV)', vendor=None, types=None, properties=[])

    >>> parse_caps("Capabilities: [40] Express (v2) Root Port (Slot-), MSI 00")
    Capability(id=64, version=-1, name='Unknown', vendor=None, types=['Express (v2) Root Port (Slot-)', 'MSI 00'], properties=[])

    >>> parse_caps("Capabilities: [300 v1] Vendor Specific Information: ID=0008 Rev=0 Len=038 <?>")
    Capability(id=768, version=1, name='Unknown', vendor=CapabilityVendor(id=8, rev=0, len=56), types=None, properties=[])

    >>> parse_caps("Capabilities: [1a0 v1] Transaction Processing Hints, Device specific mode supported, Steering table in TPH capability structure")
    Capability(id=416, version=1, name='Unknown', vendor=None, types=['Transaction Processing Hints', 'Device specific mode supported', 'Steering table in TPH capability structure'], properties=[])

    """
    assert p.startswith("Capabilities: "), p
    m = RE_CAPS.match(p)
    (cap, v, name) = m.groups()
    if not v:
        v = -1
    else:
        assert v.startswith(' v'), (v, p)
        v = int(v[2:])

    vendor = None
    types = None
    if name.startswith('Vendor Specific Information:'):
        mv = RE_VENDOR.match(name)
        assert mv, (name, p)
        vendor = CapabilityVendor(
                id=int(mv.group('id'), 16),
                rev=int(mv.group('rev'), 16),
                len=int(mv.group('len'), 16),
            )
        name = 'Unknown'

    elif ', ' in name:
        types = name.split(', ')
        name = 'Unknown'

    return Capability(int(cap, 16), v, name, [], vendor=vendor, types=types)


def parse_lspci_output(output):
    output = _fixup(output)

    device_lines = group_device_lines(output.splitlines())
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
                for p in l:
                    if ': ' in p:
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

            assert isinstance(l, str), l
            assert ': ' in l, l
            name, value = l.split(': ', 1)
            if ',' in value:
                value = [v.strip() for v in value.split(',')]

            if name in FLAGS:
                value = parse_flags(value)

            details[name] = value
        print(device)
        pprint(details)
        print()
    sys.exit(1)
    return device_lines

    devices = []
    current_device = None

    lines = output.splitlines()

    for device in current_devices:
        devices[-1] = group
        groups = []
        while device[-1]:
            line = devices[-1].pop(0)

        indent = 0
        last = current_device
        while line[indent] == '\t':
            indent += 1
            assert isinstance(last, list), last
            last = last[-1]

        assert indent > 0 and line[0] == '\t', repr(line)
        if ':' in line:
            name, bits = line[indent:].split(':', 1)
            assert bits[0] in (' ', '\t'), (name, bits, line)
            last.append([name, indent, [bits[1:]]])
        else:
            assert indent == last[1]+1, (indent, last, line)
            last[-1].append(line[indent:])

    for d in devices:
        print(d[0])
        pprint(d[1:])
        print()
    return devices


    for line in lines:
        if not line.strip():
            current_device = None
            continue

        if line != line.strip():
            line = line.strip()


        if line[2] == ':':
            assert not current_device, current_device
            current_device = Device(address=line.split()[0], description="", subsystem="", control="", status="", latency="", kernel_driver="")
            devices.append(current_device)

        elif not current_device:
            print('Skipping (no device)', line)

        if ":" not in line:
            print('Skipping', line)
            continue

        key, value = line.split(":", 1)
        key = key.strip().lower().replace(" ", "_")
        value = value.strip()
        if hasattr(current_device, key):
            setattr(current_device, key, value)
            continue

    return devices


def main(args):
    try:
        output = open('lspci.vvv').read()
    except FileNotFoundError:
        import subprocess
        output = subprocess.check_output(["lspci", "-vvv"], universal_newlines=True)

    devices = parse_lspci_output(output)

    print('-'*75)

    for name, details in devices:
        print()
        print(name)
        pprint(details)

    return 0


if __name__ == "__main__":
    import doctest
    if doctest.testmod().failed > 0:
        sys.exit(1)
    sys.exit(main(sys.argv))
