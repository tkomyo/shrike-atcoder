# abc452a.py
#
# ABC452 A - Gothec / Five Sekku
# RP2040 side for Shrike FPGA
#
# SPI protocol:
#   1 byte = [cmd:2bit][unused: 1bit][data:5bit]

from machine import Pin, SPI
import time

# SPI command
CMD_NOP      = 0b00
CMD_SET_CHAR = 0b01
CMD_EOL      = 0b10
CMD_RESET    = 0b11

# MISO status
STATUS_HEADER = 0b00
STATUS_BODY   = 0b01
STATUS_EOL    = 0b10

def make_frame(cmd, data=0):
    return ((cmd & 0b11) << 6) | (data & 0b111111)

def char_to_code(c):
    return ord(c) - ord('a')

def code_to_char(x):
    return chr(ord('a') + x)

# Shrike SPI pins
spi = SPI(
    0,
    baudrate=1_000_000,
    polarity=0,
    phase=0,
    sck=Pin(2),
    mosi=Pin(3),
    miso=Pin(0),
)

ss = Pin(1, Pin.OUT)
ss.value(1)

def spi_transfer(byte):
    tx = bytes([byte])
    rx = bytearray(1)

    ss.value(0)
    spi.write_readinto(tx, rx)
    ss.value(1)

    # short gap for safety
    time.sleep_us(10)

    return rx[0]

def send_cmd(cmd, data=0):
    return spi_transfer(make_frame(cmd, data))

def read_result():
    rx = send_cmd(CMD_NOP, 0)
    status = (rx >> 6) & 0b11
    data = rx & 0b111111
    return status, data

def solve(s):
    ans = []

    # Reset FPGA internal state
    send_cmd(CMD_RESET, 0)
    read_result()  # optional flush

    for c in s:
        code = char_to_code(c)

        # Send character. Return value is ignored.
        send_cmd(CMD_SET_CHAR, code)

        # Read result prepared by FPGA.
        status, data = read_result()

        if status == STATUS_BODY:
            ans.append(code_to_char(data & 0b11111))
        elif status == STATUS_HEADER:
            pass
        elif status == STATUS_EOL:
            break

    # Send EOL and read EOL response
    send_cmd(CMD_EOL, 0)
    status, data = read_result()

    return ''.join(ans)

# Test
while True:
    s = input("S> ").strip()

    if s == "exit":
        break

    ans = solve(s)
    print("ANS:", repr(ans))