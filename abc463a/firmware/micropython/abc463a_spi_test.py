# abc463a_rp_spi.py
#
# ABC463A Shrike RP2040 side
#
# MOSI frame: 16bit
#   [15:13] CMD
#   [12:10] AUX
#   [9:0]   DATA
#
# Each command is sent as 2 SPI bytes.
#
# MISO response:
#   0x00 = WAIT
#   0x80 = REPLY + No
#   0x81 = REPLY + Yes

from machine import Pin, SPI
import time


# ------------------------------------------------------------
# SPI pin settings
# Based on Shrike gpio_extender_8bit style wiring
# ------------------------------------------------------------

SPI_ID = 0

PIN_MISO = 0
PIN_CS   = 1
PIN_SCK  = 2
PIN_MOSI = 3

spi = SPI(
    SPI_ID,
    baudrate=1_000_000,
    polarity=0,
    phase=0,
    sck=Pin(PIN_SCK),
    mosi=Pin(PIN_MOSI),
    miso=Pin(PIN_MISO),
)

cs = Pin(PIN_CS, Pin.OUT)
cs.value(1)


# ------------------------------------------------------------
# Command definitions
# ------------------------------------------------------------

CMD_NOP   = 0b000
CMD_SET_X = 0b001
CMD_SET_Y = 0b010
CMD_DEBUG = 0b101
CMD_RESET = 0b111

WAIT = 0x00
REPLY_FLAG = 0x80
RESULT_BIT = 0x01


# ------------------------------------------------------------
# Frame utilities
# ------------------------------------------------------------

def make_frame(cmd, aux=0, data=0):
    """
    Make 2-byte MOSI frame.

    byte0 = { CMD[2:0], AUX[2:0], DATA[9:8] }
    byte1 = { DATA[7:0] }
    """
    data &= 0x3ff
    aux &= 0x07
    cmd &= 0x07

    byte0 = (cmd << 5) | (aux << 2) | ((data >> 8) & 0x03)
    byte1 = data & 0xff

    return bytearray([byte0, byte1])


def spi_transfer_2bytes(tx):
    """
    Send 2 bytes and receive 2 bytes.
    CS is toggled once per 2-byte logical frame.
    """
    rx = bytearray(2)

    cs.value(0)
    spi.write_readinto(tx, rx)
    cs.value(1)

    # Small gap between frames.
    time.sleep_us(10)

    return rx


def send_cmd(cmd, aux=0, data=0, label=""):
    tx = make_frame(cmd, aux, data)
    rx = spi_transfer_2bytes(tx)

    if label:
        print(
            "{:<10} TX=[0x{:02X}, 0x{:02X}]  RX=[0x{:02X}, 0x{:02X}]".format(
                label, tx[0], tx[1], rx[0], rx[1]
            )
        )

    return rx


def pick_reply(rx):
    """
    The design expects both RX bytes of NOP result to show REPLY.
    If timing differs, rx[0] | rx[1] still picks up the reply.
    """
    return rx[0] | rx[1]


def decode_reply(reply):
    if (reply & REPLY_FLAG) == 0:
        return "WAIT"

    result = reply & RESULT_BIT
    if result:
        return "Yes"
    else:
        return "No"


# ------------------------------------------------------------
# ABC463A transaction
# ------------------------------------------------------------

def expected_answer(x, y):
    return "Yes" if x * 9 == y * 16 else "No"


def run_case(x, y):
    print()
    print("===== X={}, Y={} =====".format(x, y))

    # Measurement range:
    #   start: just before first MOSI RESET
    #   end  : just after final MOSI RESET
    t0 = time.ticks_us()

    rx_reset_1 = send_cmd(CMD_RESET, data=0, label="RESET")
    rx_nop_1   = send_cmd(CMD_NOP,   data=0, label="NOP")

    rx_set_x   = send_cmd(CMD_SET_X, data=x, label="SET_X")
    rx_set_y   = send_cmd(CMD_SET_Y, data=y, label="SET_Y")

    rx_reply   = send_cmd(CMD_NOP,   data=0, label="NOP_REPLY")
    rx_clear   = send_cmd(CMD_NOP,   data=0, label="NOP_CLEAR")

    rx_reset_2 = send_cmd(CMD_RESET, data=0, label="RESET")

    elapsed_us = time.ticks_diff(time.ticks_us(), t0)

    reply = pick_reply(rx_reply)
    answer = decode_reply(reply)

    print("reply byte : 0x{:02X}".format(reply))
    print("FPGA answer:", answer)
    print("Expected   :", expected_answer(x, y))
    print("elapsed    :", elapsed_us, "us")

    if answer == expected_answer(x, y):
        print("RESULT     : PASS")
    else:
        print("RESULT     : FAIL")

    return answer


# ------------------------------------------------------------
# Test cases
# ------------------------------------------------------------

tests = [
    (16, 9),
    (32, 18),
    (4, 3),
    (1000, 562),
    (1000, 563),

    # AtCoder sample cases
    (800, 450),   # Yes
    (234, 108),   # No
    (108, 192),   # No
]

for x, y in tests:
    run_case(x, y)