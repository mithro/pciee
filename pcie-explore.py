#!/usr/bin/env python3

import os
import pprint
import subprocess
import sys

COLS = int(os.environ.get('COLS', '80'))

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


def parents(start, end, regions):
    """
    >>> regions = {}
    >>> a = (0, 1000)
    >>> b = (2000, 3000)
    >>> 
    >>> parents(*a, regions)
    >>> parents(*b, regions)
    >>> list(regions.keys())
    [(0, 1000), (2000, 3000)]
    >>> parents(100, 200, regions)
    >>> list(regions.keys())
    [(0, 1000), (2000, 3000)]
    >>> list(sorted(regions[a].keys()))
    [(100, 200)]
    >>> parents(50, 75, regions)
    >>> list(sorted(regions[a].keys()))
    [(50, 75), (100, 200)]
    >>> parents(2000, 2100, regions)
    >>> list(regions.keys())
    [(0, 1000), (2000, 3000)]
    >>> list(sorted(regions[b].keys()))
    [(2000, 2100)]
    >>> parents(2000, 2001, regions)
    >>> list(sorted(regions[b].keys()))
    [(2000, 2100)]
    >>> parents(200, 300, regions)
    >>> parents(100, 150, regions)
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


#import doctest
#if not doctest.testmod():
#    sys.exit(1)


try:
    data_iomem = open('iomem', encoding='utf-8').read()
except FileNotFoundError:
    p = subprocess.Popen(['sudo', 'cat', '/proc/iomem'], stdout=subprocess.PIPE, encoding='utf-8')
    data_iomem, _ = p.communicate()

try:
    data_lspci = open('lspci', encoding='utf-8').read()
except FileNotFoundError:
    p = subprocess.Popen(['lspci', '-PPP'], stdout=subprocess.PIPE, encoding='utf-8')
    data_lspci, _ = p.communicate()


mem = {}
hmem = []

m = len('39c000000000')

def lpad(s, n, l):
    while len(s) < l:
        s = n+s
    return s


devices = {}
for line in data_lspci.splitlines():
    line = line.rstrip()

    slot, rest = line.split(' ', 1)
    slot = slot.split('/')
    slot.reverse()

    ptype, details = rest.split(': ', 1)

    devices[slot[0]] = (slot, ptype, details)


for line in data_iomem.splitlines():
    line = line.rstrip()

    addr, info = line.split(' : ', 1)

    i = 0
    while addr[0] == ' ':
        i += 1
        addr = addr[1:]

    start, end = addr.split('-')

    istart = eval('0x'+start)
    iend = eval('0x'+end)
    isize = iend-istart+1

    region = (istart, isize, iend, i)

    if info.startswith('0000:'):
        info = info[5:]
        if info in devices:
            info = info + ' ' + devices[info][-1]

    if info.startswith('PCI Bus 0000:'):
        busno = info[13:]+':00.0'
        if busno in devices:
            info = info + ' ' + devices[busno][-1]
        else:
            info = info + ' ?????? ' + repr(busno)

    if region not in mem:
        mem[region] = [info,]
    else:
        mem[region].append(info)


smem = []
for (istart, size, iend, i), info in sorted(mem.items()):
    smem.append((istart, iend, info))


tree = {}
for start, end, info in sorted(smem, key=lambda x: (x[0], 0xffffffffffff-x[1], x[2])):
    d = parents(start, end, tree)
    if (0, 0) not in d:
        d[(0,0)] = []
    d[(0,0)].extend(info)


F = 0xffffffffffff
rend = [F]

def pmem(region, i=0):
    for (istart, iend), d in region.items():
        if (istart, iend) == (0, 0):
            continue

        isize = iend-istart+1

        hstart = lpad(hex(istart)[2:], '0', m)
        hend   = lpad(hex(iend)[2:], '0', m)
        hsize  = lpad(hex(isize)[2:], ' ', m)

        info = d.get((0, 0), [])

        if 'DMI2' in repr(info) or 'Root Port' in repr(info):
            print()
            print()
            rend[0] = iend+1
        elif istart >= rend[0]:
            print()
            print()
            rend[0] = F

        p1 = ' '*i
        p2 = ' '*(5-i)

        print('|', p1, hstart, hend, p2, '|', hsize, '|', p1, info) #" && ".join(info))

        if len(d) == 1:
            continue

        pmem(d, i+1)

pmem(tree)
