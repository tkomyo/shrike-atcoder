from machine import Pin, SPI
import time

# --- SPI pin configuration ---
sck_pin  = Pin(2)
mosi_pin = Pin(3)
miso_pin = Pin(0)
ss_pin   = Pin(1, Pin.OUT, value=1)
rst_pin  = Pin(14, Pin.OUT, value=1)

spi = SPI(0, baudrate=1_000_000, sck=sck_pin, mosi=mosi_pin, miso=miso_pin)

ADDR_ABC086A = 0x5

def send_cmd(addr, data):
    packet = (addr << 4) | (data & 0x0F)

    tx = bytes([packet])
    rx = bytearray(1)

    ss_pin.value(0)
    spi.write_readinto(tx, rx)
    ss_pin.value(1)

    return rx[0]

def reset_fpga_core():
    rst_pin.value(0)
    time.sleep(0.05)
    rst_pin.value(1)
    time.sleep(0.05)

def solve_abc086a(a, b):
    # ABC086A:
    # a * b is odd if both a and b are odd.
    a0 = a & 1
    b0 = b & 1

    # data[0] = a0, data[1] = b0
    data = a0 | (b0 << 1)

    # 1st SPI transfer: write a0, b0 to FPGA
    send_cmd(ADDR_ABC086A, data)

    # 2nd SPI transfer: dummy read to receive result
    result = send_cmd(0x0, 0x0)

    return "Odd" if (result & 0x01) else "Even"

# --- main ---
reset_fpga_core()

line = input()
a, b = map(int, line.split())

print(solve_abc086a(a, b))