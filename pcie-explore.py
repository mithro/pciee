#!/usr/bin/env python3

import subprocess
import pprint

p = subprocess.Popen(['sudo', 'cat', '/proc/iomem'], stdout=subprocess.PIPE, encoding='utf-8')
data_iomem, _ = p.communicate()

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

    region = (istart, iend, isize)
    mem[region] = info

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

    hregion = (' '*i, lpad(start, '0', m), lpad(end, '0', m), lpad(hex(isize)[2:], ' ', m))
    hmem.append((hregion, info))

pprint.pprint(devices)

print()

for (l, start, end, size), info in hmem:
    if len(l) == 0:
        print()
    print(l, start, end, (10-len(l))*' ', size, l, info)
