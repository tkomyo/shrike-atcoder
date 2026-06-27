from machine import Pin, SPI
import time


# Shrike / RP2040 SPI pin assignment
PIN_MISO = 0
PIN_CS = 1
PIN_SCK = 2
PIN_MOSI = 3
PIN_RST_N = 14

SPI_ID = 0
SPI_BAUDRATE = 1_000_000
BYTE_GAP_US = 20
USE_HW_RESET = True


# MOSI: [7:5] CMD, [4:1] reserved, [0] DATA
CMD_NOP = 0b000
CMD_DATA = 0b001
CMD_EOD = 0b010
CMD_DEBUG = 0b101
CMD_RESET = 0b111

REPLY_WAIT = 0x00
REPLY_WEST = 0x80
REPLY_EAST = 0x81


spi = SPI(
    SPI_ID,
    baudrate=SPI_BAUDRATE,
    polarity=0,
    phase=0,
    bits=8,
    firstbit=SPI.MSB,
    sck=Pin(PIN_SCK),
    mosi=Pin(PIN_MOSI),
    miso=Pin(PIN_MISO),
)

cs = Pin(PIN_CS, Pin.OUT, value=1)

if USE_HW_RESET:
    rst_n = Pin(PIN_RST_N, Pin.OUT, value=1)
else:
    rst_n = None


def hw_reset():
    if rst_n is None:
        return

    rst_n.value(0)
    time.sleep_ms(5)
    rst_n.value(1)
    time.sleep_ms(5)


def make_frame(cmd, bit=0):
    return ((cmd & 0b111) << 5) | (bit & 0b1)


def bin8(x):
    s = ""
    for i in range(7, -1, -1):
        s += "1" if ((x >> i) & 1) else "0"
    return s


def hex8(x):
    digits = "0123456789ABCDEF"
    x &= 0xFF
    return "0x" + digits[(x >> 4) & 0xF] + digits[x & 0xF]


def pad_right(s, width):
    while len(s) < width:
        s += " "
    return s


def spi_xfer(byte):
    rx = bytearray(1)
    tx = bytes([byte & 0xFF])

    cs.value(0)
    spi.write_readinto(tx, rx)
    cs.value(1)

    time.sleep_us(BYTE_GAP_US)
    return rx[0]


def xfer(label, byte, log=True):
    rx = spi_xfer(byte)
    if log:
        print(
            pad_right(label, 18)
            + " TX=" + hex8(byte) + " " + bin8(byte)
            + "  RX=" + hex8(rx) + " " + bin8(rx)
        )
    return rx


def send_reset(log=True):
    return xfer("RESET", make_frame(CMD_RESET), log)


def send_nop(log=True):
    return xfer("NOP", make_frame(CMD_NOP), log)


def send_data(ch, log=True):
    if ch == "E":
        bit = 1
    elif ch == "W":
        bit = 0
    else:
        raise ValueError("S must consist of only E and W")

    return xfer("DATA " + ch, make_frame(CMD_DATA, bit), log)


def send_eod(log=True):
    return xfer("EOD", make_frame(CMD_EOD), log)


def send_debug(log=True):
    return xfer("DEBUG", make_frame(CMD_DEBUG), log)


def signed8(x):
    x &= 0xFF
    if x & 0x80:
        return x - 0x100
    return x


def expected_diff(s):
    diff = 0
    for ch in s:
        if ch == "E":
            diff += 1
        elif ch == "W":
            diff -= 1
        else:
            raise ValueError("S must consist of only E and W")
    return diff


def expected_answer(s):
    if expected_diff(s) > 0:
        return "East"
    return "West"


def read_result(log=True):
    rx = xfer("READ result", make_frame(CMD_NOP), log)
    if rx == REPLY_EAST:
        return "East"
    if rx == REPLY_WEST:
        return "West"
    raise ValueError("unexpected result reply: " + hex8(rx))


def read_debug_diff(log=True):
    send_debug(log)
    rx = xfer("READ debug", make_frame(CMD_NOP), log)
    return signed8(rx)


def solve_case(s, log=True):
    send_reset(log)
    clear = send_nop(log)

    for ch in s:
        send_data(ch, log)

    send_eod(log)
    actual = read_result(log)

    send_reset(log)
    end_clear = send_nop(log)

    return actual, clear, end_clear


def run_case(name, s, expected, debug_expected=None):
    print()
    print("========================================")
    print("TEST:", name)
    print("S =", s)
    print("========================================")

    send_reset()
    clear = send_nop()
    if clear != REPLY_WAIT:
        print("WARN: post-reset NOP returned", hex8(clear))

    for ch in s:
        send_data(ch)

    if debug_expected is not None:
        actual_diff = read_debug_diff()
        if actual_diff != debug_expected:
            print("DEBUG FAIL: expected", debug_expected, "actual", actual_diff)
            send_reset()
            send_nop()
            return False
        print("DEBUG PASS: diff =", actual_diff)

    send_eod()
    actual = read_result()

    send_reset()
    clear = send_nop()
    if clear != REPLY_WAIT:
        print("WARN: end NOP returned", hex8(clear))

    ok = actual == expected
    print("expected =", expected, "actual =", actual, "=>", "PASS" if ok else "FAIL")
    return ok


def measure_case(name, s, expected, repeat=1):
    ok_count = 0
    total_us = 0
    min_us = None
    max_us = 0

    for i in range(repeat):
        start = time.ticks_us()
        actual, clear, end_clear = solve_case(s, log=False)
        elapsed = time.ticks_diff(time.ticks_us(), start)

        total_us += elapsed
        if min_us is None or elapsed < min_us:
            min_us = elapsed
        if elapsed > max_us:
            max_us = elapsed

        if actual == expected and clear == REPLY_WAIT and end_clear == REPLY_WAIT:
            ok_count += 1

    avg_us = total_us // repeat
    print(
        pad_right(name, 18)
        + " len=" + str(len(s))
        + " repeat=" + str(repeat)
        + " ok=" + str(ok_count) + "/" + str(repeat)
        + " avg_us=" + str(avg_us)
        + " min_us=" + str(min_us)
        + " max_us=" + str(max_us)
    )


def run_timing_tests():
    print()
    print("========================================")
    print("TIMING TESTS")
    print("========================================")

    measure_case("timing_single_e", "E", "East", repeat=5)
    measure_case("timing_official1", "EEWEW", "East", repeat=5)
    measure_case("timing_w_99", "W" * 99, "West", repeat=5)
    measure_case("timing_e50_w49", "E" * 50 + "W" * 49, "East", repeat=5)


def run_tests():
    cases = [
        ("sample1_official", "EEWEW", "East", None),
        ("sample2_official", "WWWWWWW", "West", None),
        ("single_east", "E", "East", None),
        ("single_west", "W", "West", None),
        ("custom_east", "EEEWW", "East", None),
        ("custom_west", "EEWWW", "West", None),
        ("length99_east", "E" * 50 + "W" * 49, "East", None),
        ("length99_west", "E" * 49 + "W" * 50, "West", None),
        ("debug_plus_one", "EWE", "East", 1),
        ("debug_minus_one", "WWE", "West", -1),
    ]

    ok_count = 0
    for name, s, expected, debug_expected in cases:
        if expected != expected_answer(s):
            print("internal expected mismatch:", name)
            continue
        if run_case(name, s, expected, debug_expected):
            ok_count += 1
        time.sleep_ms(100)

    print()
    print("========================================")
    print("SUMMARY:", ok_count, "/", len(cases), "passed")
    print("========================================")

    run_timing_tests()


def main():
    if USE_HW_RESET:
        print("Hardware reset")
        hw_reset()

    run_tests()


main()
