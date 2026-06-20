# abc452a

AtCoder ABC452 A を Vicharak Shrike FPGA + RP2040 で解く実験。

## SPI protocol

1 byte = `[cmd:2bit][data:6bit]`

- `00`: NOP / read result
- `01`: set M
- `10`: set D
- `11`: reserved

Readback:

- bit0 = yes
- bit[7:1] = 0