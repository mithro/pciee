#!/usr/bin/env python3

import pathlib

pci_ids = {}

vid = None
for l in open('/usr/share/misc/pci.ids'):
    if not l.strip():
        continue
    l = l.rstrip()
    if l.startswith('#'):
        continue
    if l.startswith('\t'):
        did, ddsc = l.strip().split(' ', 1)
        pci_ids[vid][-1][did] = ddsc.strip()
    else:
        vid, vdsc = l.split(' ', 1)
        pci_ids[vid] = (vdsc.strip(), {})


def r(f, e='?'):
    try:
        d = open(f).read().strip()
    except FileNotFoundError:
        return e
    if d.endswith(' GT/s PCIe'):
        return d[:-10]
    elif d in ('Unknown', '255'):
        return e
    else:
        return d

def h2(i):
    if type(i) == str:
        try:
            i = int(i)
        except ValueError:
            return i
    h = hex(i)[2:]
    while len(h) < 2:
        h = '0'+h
    h = h+':' #00.0'
    return h


class PCIDevice:
    bus     = None
    vendor  = None
    device  = None

    components = None


class PCIBus:
    pass

# Primary Bus Number The bus number immediately upstream of the PCI-PCI Bridge,
# Secondary Bus Number The bus number immediately downstream of the PCI-PCI Bridge,
# Subordinate Bus Number The highest bus number of all of the busses that can be reached downstream of the bridge.

#             +-1d.1-[02-03]----00.0-[03]----00.0  ASPEED Technology, Inc. ASPEED Graphics Family

# +-[0000:17]-+-00.0-[18]----00.0  Intel Corporation NVMe Datacenter SSD [3DNAND, Beta Rock Controller]
# |           +-01.0-[19]----00.0  Intel Corporation NVMe Datacenter SSD [3DNAND, Beta Rock Controller]
# |           +-02.0-[1a]----00.0  Phison Electronics Corporation PS5013 E13 NVMe Controller
# |           +-03.0-[1b]----00.0  Kingston Technology Company, Inc. Device 500f

devices = {}
for d in sorted(pathlib.Path('/sys/bus/pci/devices/').glob('*')):
    dname = d.name[5:8]

    child_bus_secondary = r(d / 'secondary_bus_number')
    child_bus_subordinate = r(d / 'subordinate_bus_number')
    if dname not in devices:
        devices[dname] = {'devices':{}}

    pclass = r(d / 'class')[2:]
    pvendor = r(d / 'vendor')[2:]
    pdevice = r(d / 'device')[2:]

    if pvendor in pci_ids:
        if pdevice in pci_ids[pvendor][-1]:
            pdevice = (pdevice, pci_ids[pvendor][-1][pdevice])
        else:
            pdevice = (pdevice, '??? - Unknown device?')
        pvendor = (pvendor, pci_ids[pvendor][0])
    else:
        pvendor = (pvendor, '??? - Unknown vendor?')

    devices[dname]['devices'][d.name[5:]] = (pclass, pvendor, pdevice)

    if child_bus_secondary != '?' and child_bus_subordinate != '?':
        for i in range(int(dname[:-1], 16)+1, int(child_bus_subordinate)+1):
            devices[dname][h2(i)] = None

has_parent = set()
for v in list(devices.values()):
    for k in list(v.keys()):
        if k == 'devices':
            continue
        if k not in v:
            continue
        if k not in devices:
            continue

        v[k] = devices[k]
        for k2 in list(devices[k]):
            if k2 == 'devices':
                continue
            if k2 in v:
                del v[k2]
        del devices[k]


import pprint
pprint.pprint(devices, width=150, compact=False)
print()


#for bus in sorted(pathlib.Path('/sys/devices/').glob('pci*')):
#    bname = bus.name[3:]
#    print(bname)
#    for d in sorted(bus.glob('*')):
#        if not d.name.startswith(bname):
#            print('??', d)
#            continue
for d in sorted(pathlib.Path('/sys/bus/pci/devices/').glob('*')):
        dname = d.name[5:]

        link_speed = r(d / 'current_link_speed')
        max_link_speed = r(d / 'max_link_speed')
        link_width = 'x'+r(d / 'current_link_width')
        max_link_width = 'x'+r(d / 'max_link_width')

        child_bus_secondary = h2(r(d / 'secondary_bus_number'))
        child_bus_subordinate = h2(r(d / 'subordinate_bus_number'))
        child_bus = (child_bus_secondary, child_bus_subordinate)
        if child_bus_secondary != child_bus_subordinate:
            pass
        if child_bus_secondary == '?' and child_bus_subordinate == '?':
            child_bus = None

        pclass = r(d / 'class')[2:]
        pvendor = r(d / 'vendor')[2:]
        pdevice = r(d / 'device')[2:]

        if pvendor in pci_ids:
            if pdevice in pci_ids[pvendor][-1]:
                pdevice = (pdevice, pci_ids[pvendor][-1][pdevice])
            else:
                pdevice = (pdevice, '??? - Unknown device?')
            pvendor = (pvendor, pci_ids[pvendor][0])
        else:
            pvendor = (pvendor, '??? - Unknown vendor?')

        res = []
        try:
            N = '0x0000000000000000'
            for l in open(d / 'resource'):
                a, b, c = l.strip().split(' ')
                if a == N and b == N and c == N:
                    continue
                res.append((a, b, c))
        except FileNotFoundError:
            pass
        res.sort()

        if 'Root Port' in pdevice[-1]:
            print()
            print('-----')
            print()

        print('  ', dname, (pclass, pvendor, pdevice), '%s/%s' % (link_speed, max_link_speed), '%s/%s' % (link_width, max_link_width))
        if child_bus:
            print('    -> ', child_bus)
        for start, end, size in res:
            print('    ', start, end, size)

#    pbus = bus / 'pci_bus' / bname
#    print() #list(sorted(pbus.glob('*'))))

