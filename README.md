Experiments in understanding PCIe

"Chassis" (case with motherboard, etc) I currently have;
 * Supermicro SuperServer 4028GR-TVRT
 * Supermicro SuperStorage SSG-6049P-E1CR60L
 * IBM AC922 8335-GTH
 * Dell PowerEdge C410x

The Supermicro 4028GR-TVRT has 2 x `PEX 9765` (65 lane, 17 port, PCI Express Gen3 ExpressFabric Platform) switches in it.

The Dell C410X has 4 x `PEX 8696` (96-Lane, 24-Port PCI Express Gen 2 - 5.0 GT/s) switches in it.

The IBM AC922 8335-GTH has a `PEX 8733` (32-Lane, 18-Port PCI Express Gen 3 - 8 GT/s) switch in it.

I also have the following "expansion cards";

 * Supermicro `AOC-SLG3-8E2P` which has a Microsemi / SwitchTec `PM8562` (Switchtec PFX-L Fanout 32xG3 PCIe Switch) on it.
 * Linkreal `LRNV9349-8I` which has a `PEX 8749` (48-Lane, 18-Port PCI Express Gen 3 - 8 GT/s) switch on it.
 * One Stop Solutions `OSS-PCIE-HIB38-X16` which has a `PEX 8733` (32-Lane, 18-Port PCI Express Gen 3 - 8 GT/s) switch in it.
 * Bunch of Qnap combined GigE / M.2 NVMe hardware.

I try to track this stuff in a [Google PCIe Switches Spreadsheet](https://docs.google.com/spreadsheets/d/1jZSAkNcLNtgT6uFQ9R1RPruqZ5_6tXa-Wqumv7s1jpU/edit#gid=1524818223) which should be publicly accessible.
