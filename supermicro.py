#!/usr/bin/env python3

from dataclasses import dataclass, astuple, asdict
from enum import Enum

import re

TO_DECODE = """\
A1SAM-2550F
A1SAi-2550F

C7X99-OCE-F

X10DDW-i
X10DDW-iN
X10DRG-H
X10DRH-C
X10DRT-H
X10DRT-P
X10DRU-X
X10DRU-XLL
X10DRU-i+
X10DRW-i
X10DRi
X10SLA-F
X10SLE-DF
X10SLH-F
X10SLL-F
X10SRG-F

X9SRG-F
X9SRL-F
X9SRW-F
X9SRi-F

X8SIE-F
X8SIL-F

X12STL-IF
X12SDV-10C-SPT4F
X12SDV-4C-SPT4F
X12SDV-8C-SPT4F

X12SDV-10C-SP6F
X12SDV-4C-SP6F
X12SDV-8C-SP6F
X12SDV-8CE-SP4F

X12SCZ-QF
X12SCZ-F
X12SCZ-TLN4F
X12STL-F
X12STH-F
X12STH-LN4F
X12STH-SYS
X12SPM-LN4F
X12SPM-LN6TF
X12SPM-TF
X12SPZ-LN4F
X12SPZ-SPLN6F
X12SDV-4C-SPT8F
X12SDV-8C-SPT8F
X12SDV-14C-SPT8F
X12SDV-16C-SPT8F
X12SDV-20C-SPT8F

X12SCA-F
X12SCA-5F
X12SPI-TF
X12SPL-F
X12SPL-LN4F
X12SPO-F
X12SPO-NTF
X12DPL-i6
X12DPL-NT6

X12SPA-TF
X12DAI-N6
X12DPi-N6
X12DPi-NT6

X12STW-F
X12STW-TF
X12SPW-F
X12SPW-TF
X12DDW-A6

X12DPT-B6
X12DPFR-AN6

X12STD-F
X12STE-F
X12SPG-NF
X12SPT-G
X12SPT-GC
X12SPT-PT
X12SPED-F
X12DGQ-R
X12DHM-6
X12DPD-A6M25
X12DPG-QBT6
X12DPG-QT6
X12DPG-U6
X12DPT-PT46
X12DPT-PT6
X12DPU-6
X12DGO-6
X12DGU
X12DPG-AR
X12DPG-OA6
X12DPG-QR
X12DSC-6

X12QCH+

"""


# UP Motherboards (Server)
#  Gen & CPU
#  Num CPUs
#  Socket
#  Arch
#  Feature
# --
#  Gen & CPU
#  Num CPUs
#  Chipset
#  Arch
#  Feature

# UP Motherboards (Workstation)
#  Platform
#  Num CPUs
#  Socket
#  Product
#  Form Factor
#  Feature

# UP Motherboards (Desktop)
#  Platform
#  Socket
#  Chipset
#  Product
#  Form Factor
#  Feature

# UP Motherboards (Embedded)
#  Gen & CPU
#  Num CPUs
#  Chipset
#  Form Factor
#  Feature

class CPUType(Enum):
 X = 'Intel Xeon Processors'
 A = 'Intel Atom Processors'
 C = 'Intel Consumer/Desktop Processors?'


class GenerationAndCPU(Enum):
 """Positions 1 and 2."""
 # UP Motherboards (Server)
 X13 = '13th gen. Xeon® Scalable Processors'

 X12 = ('12th gen. Xeon® (E-2300 Rocket Lake)'
        '12th gen. Xeon® Scalable Processors')

 X11 = ('11th gen. Xeon® (E-2100/2200 Coffee Lake)'
        '11th gen. Xeon® (E3-1200 v6/v5)'
        '11th gen. Xeon® Scalable Processors')

 X10 = ('10th gen. Xeon® (E3-1200 v4/v3)'
        '10th gen. Xeon® (E5-2600 v4/v3, E5-1600 v3)'
        '10th gen. Xeon® (E5-2600 v4/v3, E5-1600 v4/v3)')

 X9  =  ' 9th gen. Xeon® (E5-2600 v2/E5-2600, E5-1600 v2)'
 X8  =  ' 8th gen. Xeon® (QPI 6.4 GT/s)'

 # UP Motherboards (Workstation)
 #X11 = '11th gen. Workstation'
 #X10 = '10th gen. Xeon® (E3-1200 v4/v3)'
 #X9 = ' 9th gen. Xeon® (E5-2600 v2/E5-2600, E5-1600 v2)'
 #X8 = ' 8th gen. Xeon® (QPI 6.4 GT/s)'

 # UP Motherboards (Embedded)
 #X11 = ('11th gen. Xeon® D-2100, E-2100, Core, Pentium or Celeron'
 #       '11th gen. Xeon® D-2100, E-2100 SoC')
 #X10 = ('10th gen. Xeon® D-1500, E3 v6/v5, Core, Pentium or Celeron'
 #       '10th gen. Xeon® D-1500, E3 v6/v5 SoC')
 A1  =  'Intel® Atom™ Processor C2000 Series or C2000 SoC Series'
 A2  =  'Intel® Atom™ Processor C3000 or E3900 SoC Series'

 # UP Motherboards (Desktop)
 # None...


class NumberOfCPUs(Enum):
 """Position 3."""
 S = (1, 'Single processor')
 D = (2, 'Dual processor')
 Q = (4, 'Quad processor')


class SocketAndChipset(Enum):
 """Position 4."""
 # UP Motherboards (Server)
 A = 'Workstation'

 C = 'Coffee Lake (LGA-1511 X11SC_series Mehlow)'
 #C = 'Cougar Point'

 I = 'Ibex Peak (3420/3400)'

 L = 'Lynx Point (LGA-1150 X10SL_series Denlow)'
 #L = 'Lynx Point'

 P = 'Purley with Socket P (X11)'
 #P = 'Socket P0 (LGA-3647 X11SP_series Purley)'
 #P = 'Socket P4 (LGA-4189 X12SP_series Whitley)'

 R = 'Grantley with Socket R3 (X10)'
 #R = 'Patsburg with Socket R (X9)'
 #R = 'Socket R3 (LGA-2011 X10SR_series Grantley)'
 #R = 'Socket R4 (LGA-2066 X11SR_series Basin Fall)'

 S = 'SkyLake (X11 Greenlow)'
 #S = 'Skylake (LGA-1511 X11SS_series Greenlow)'

 T = 'Rocket Lake (LGA-1200 X11ST_series Tatlow)'
 #T = 'Tylersburg (X58)'

 # UP Motherboards (Workstation)
 #A = 'Socket H'
 #C = 'Socket H'
 #R = 'Socket R'

 # UP Motherboards (Embedded)
 #A = 'Apollo Lake for A2 or Avoton for A1'
 #B = 'Bay Trail for X10, Braswell for X11'
 #C = 'Coffee Lake'
 #D = 'Xeon D or Atom C3000'
 #L = 'Lynx Point, Haswell'
 #R = 'Rangeley'
 #S = 'Sky Lake or Kaby Lake'

 # UP Motherboards (Desktop)
 #_7 = 'Socket H'
 #_9 = 'Socket R'
 # Note: C7X99 series is exception, it is Socket R
 #PG = 'Pro Gaming'
 #CG = 'Core Gaming'
 #CB = 'Core Business'



class Architecture(Enum):
 """Position 5.

  * Arch
  * Product
  * Form Factor
 """
 # UP Motherboards (Server)
 #  Architecture / Application / Feature
 i = 'SATA only'
 I = 'Mainstream'
 L = 'Cost Optimized / Low Cost'
 M = 'Micro ATX'
 G = 'GPU Optimized'
 O = 'Optimized for high-performance storage'
 T = 'Twin Architecture'

 FR = 'Rear IO / Front IO of FatTwin Architecture'
 W = 'WIO Architecture'
 U = 'UIO Architecture'
 DW = 'CloudDC'
 D = 'MicroCloud Architecture'

 A = 'Legacy PCI support (as in X10SSA-F)'
 #A = 'Legacy / WS for Socket B2/R/H2/H3/H4'

 H = 'Alternative 1'
 E = 'Alternative 2'
 V = 'Alternative 3'

 # UP Motherboards (Embedded)
 #  Form Factor / Application/Feature
 #i = 'Mini-ITX'
 #A = 'Mini-ITX'
 #V = 'Mini-ITX or Flex ATX'
 N = '3.5" SBC, 4" x 5.75"'
 P = '2.5" SBC'
 #E = 'MicroCloud Architecture'
 #D = 'MicroCloud Architecture'
 Z = 'Micro ATX, 1U Optimized'
 Q = 'Miro ATX Core i7, 2U Application'

 # UP Motherboards (Desktop)
 #  Position 5 - Form Factor
 #M = 'uATX'
 #I = 'mini ITX'
 _ = 'ATX'



@dataclass
class Networking:
    # BaseT == Copper / Category 5/6/7
    # SFP == Small Form-factor Pluggable modules

    # 10 gigabit
    BaseT_10G: int = 0
    SFP_10G: int = 0

    # 1 gigabit
    BaseT_1G: int = 0
    SFP_1G: int = 0

    # 100 megabit
    BaseT_100M: int = 0
    SFP_100M: int = 0

    def __repr__(self):
        s = ['Networking(']
        for k, v in asdict(self).items():
            if v == 0:
                continue
            s.append(f'{k}={v}')
            s.append(', ')
        if s[-1] == ', ':
            s.pop(-1)
        s.append(')')
        return ''.join(s)

    @property
    def ports(self):
        """

        >>> n = Networking()
        >>> n
        Networking()
        >>> n.ports
        0
        >>> n.BaseT_10G = 2
        >>> n
        Networking(BaseT_10G=2)
        >>> n.ports
        2
        >>> n.BaseT_1G = 6
        >>> n
        Networking(BaseT_10G=2, BaseT_1G=6)
        >>> n.ports
        8
        """
        return sum(astuple(self))



def decode_features(f):
    """
    TLN2F  = '2 x 10GBase-T,              , w/IPMI'
    TLN4F  = '2 x 10GBase-T,  2 x 1GbE LAN, w/IPMI'
    TLN4Fp = '2 x 10GSFP+  ,  2 x 1GbE LAN, w/IPMI'
    TLN5F  = '4 x 10GBase-T,  1 x 1GbE LAN, w/IPMI'
    LN4F   = '                4 x 1GbE LAN, w/IPMI'
    LN8F   = '                8 x 1GbE LAN, w/IPMI'
    LN10PF = '2 x SFP,       10 x 1GbE LAN, w/IPMI'
    TP4F   = '2 x 10GSFP+  ,  4 x      LAN, w/IPMI'
    TP8F   = '2 x 10GSFP+  ,  8 x      LAN, w/IPMI' # ??? -- X11/A2 with dual 10GBase-T
    M4F    = '                4 x 1GbE LAN, w/IPMI'
    F      = '                2 x      LAN, w/IPMI'
    M4     = '                4 x 1GbE LAN, w/AMT'

    >>> decode_features('TLN2F')
    ['IPMI', Networking(BaseT_10G=2)]
    >>> decode_features('TLN4F')
    ['IPMI', Networking(BaseT_10G=2, BaseT_1G=2)]
    >>> decode_features('TLN4F+')
    >>> decode_features('TLN5F')
    ['IPMI', Networking(BaseT_10G=5, BaseT_1G=1)]
    >>> decode_features('LN4F')
    >>> decode_features('LN8F')
    >>> decode_features('LN10PF')
    >>> decode_features('TP4F')
    >>> decode_features('TP8F')
    >>> decode_features('M4F')

    >>> for f in TO_DECODE.splitlines():
    ...     if f.strip():
    ...         print(f, decode_features(f.rsplit('-')[-1]))
    """
    features = []
    if 'F' in f:
        assert f[-1] == 'F', f
        f = f[:-1]
        features.append('IPMI')

    m = re.match('(T|TP|)LN([0-9]+)([+]?)', f)
    if m:
        highspeed = m.group(1)
        number = int(m.group(2))
        plus = m.group(1)

        network = Networking()

        if highspeed == 'TP':
            network.SFP_10G += 2
        elif highspeed == 'T':
            network.BaseT_10G += 2

        network.BaseT_1G = number - network.ports
        features.append(network)

    return features


class Feature(Enum):
 """ Position 6 -- Form factor. """

 # UP Motherboards (Server)
 F = 'IPMI'

 X = 'PCIX'

 _6 = 'SAS2 (6Gbps)'
 _7 = 'Broadcom SAS 6Gbps'
 C = 'Broadcom SAS 12Gbps'

 LN2 = 'Two LANs'
 LN4 = 'Four LANs'
 LN5 = 'Five LANs'
 LN6 = 'Six LANs'
 LN8 = 'Eight LANs'

 T  = '10Gb LAN'
 TP = '10Gb SFP+'

 I = 'mini-ITX form factor'
 S = 'Cost Optimized'
 N = 'NVMe support'

 D = 'Dual Nodes'
 G = 'Grand Twin'
 B = 'Big Twin'

 A = 'AIOM'
 V = 'VMD/VROC'

 #N = 'NVMe support'
 #G = 'Intel Graphics'
 #V = 'VMD/VROC'

 # UP Motherboards (Workstation)
 #A, E = 'Workstation'

 # UP Motherboards (Embedded)

 Q = 'Q170 or Q370 PCH with AMT support'

 L = 'Low cost SKU'
 H = 'High Performance SKU'
 E = 'Extended Temperature Support'

 # UP Motherboards (Desktop)
 #  Feature - Position 6
 W = 'WiFi'



if __name__ == "__main__":
    import doctest
    doctest.testmod()
