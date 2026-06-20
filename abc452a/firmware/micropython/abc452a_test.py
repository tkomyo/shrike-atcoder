# abc452a.py
#
# ABC452 A - Gothec / Five Sekku
# RP2040 side for Shrike FPGA
#
# SPI protocol:
#   1 byte = [cmd:2bit][data:6bit]
#
#   cmd 00: NOP / read result
#   cmd 01: set M
#   cmd 10: set D
#   cmd 11: reserved
#
# Transaction:
#   send 0x40 | M
#   send 0x80 | D
#   send 0x00
#   result = rx[2] & 1

from machine import Pin, SPI
import time


# --- Hardware Configuration ---
# Based on confirmed Shrike / RP2040 mapping
sck_pin  = Pin(2)
mosi_pin = Pin(3)
miso_pin = Pin(0)
ss_pin   = Pin(1, Pin.OUT, value=1)
rst_pin  = Pin(14, Pin.OUT, value=1)


# --- SPI Configuration ---
spi = SPI(
    0,
    baudrate=1_000_000,
    polarity=0,
    phase=0,
    bits=8,
    firstbit=SPI.MSB,
    sck=sck_pin,
    mosi=mosi_pin,
    miso=miso_pin,
)


# --- Command Constants ---
CMD_NOP   = 0b00 << 6
CMD_SET_M = 0b01 << 6
CMD_SET_D = 0b10 << 6


def reset_fpga():
    """Reset FPGA-side logic if rst_n is connected."""
    rst_pin.value(0)
    time.sleep_ms(10)
    rst_pin.value(1)
    time.sleep_ms(10)


def fpga_query(m, d):
    """Send M,D to FPGA and read yes bit."""

    if not (1 <= m <= 12):
        raise ValueError("M must be in 1..12")
    if not (1 <= d <= 31):
        raise ValueError("D must be in 1..31")

    tx = bytearray([
        CMD_SET_M | m,
        CMD_SET_D | d,
        CMD_NOP,
    ])
    rx = bytearray(3)

    ss_pin.value(0)
    time.sleep_us(1)
    spi.write_readinto(tx, rx)
    time.sleep_us(1)
    ss_pin.value(1)

    return rx[2] & 1


def solve_once():
    line = input().strip()
    m, d = map(int, line.split())

    yes = fpga_query(m, d)
    print("Yes" if yes else "No")


def self_test():
    tests = [
        (1, 7, "Yes"),
        (3, 3, "Yes"),
        (5, 5, "Yes"),
        (7, 7, "Yes"),
        (9, 9, "Yes"),
        (1, 1, "No"),
        (3, 7, "No"),
        (12, 31, "No"),
    ]

    for m, d, expected in tests:
        actual = "Yes" if fpga_query(m, d) else "No"
        print(m, d, actual, "OK" if actual == expected else "NG")


# --- Main ---

reset_fpga()

# AtCoder-style single input
# solve_once()

# Debug:
self_test()