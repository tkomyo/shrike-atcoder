from machine import Pin, SPI
import time

# ============================================================
# Shrike / RP2040 SPI pin assignment
# ============================================================
PIN_MISO = 0
PIN_CS   = 1
PIN_SCK  = 2
PIN_MOSI = 3
PIN_RST_N = 14

SPI_ID = 0
SPI_BAUDRATE = 1_000_000
BYTE_GAP_US = 20

USE_HW_RESET = True

# ============================================================
# Protocol
#
# MOSI: [7:5] CMD, [4:0] DATA
# MISO: [7] STATE/VALID, [6:1] AUX, [0] DATA/result
# ============================================================
CMD_NOP   = 0b000
CMD_SET_X = 0b001
CMD_SET_S = 0b010
CMD_DEBUG = 0b101
CMD_RESET = 0b111


# ============================================================
# SPI setup
# ============================================================
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


# ============================================================
# Utility functions
# ============================================================
def hw_reset():
    if rst_n is None:
        return

    rst_n.value(0)
    time.sleep_ms(5)
    rst_n.value(1)
    time.sleep_ms(5)


def make_cmd(cmd, data=0):
    return ((cmd & 0b111) << 5) | (data & 0b11111)


def bin_bits(x, width):
    s = ""
    for i in range(width - 1, -1, -1):
        if (x >> i) & 1:
            s += "1"
        else:
            s += "0"
    return s


def bin8(x):
    return bin_bits(x & 0xFF, 8)


def bin5(x):
    return bin_bits(x & 0x1F, 5)


def hex_digit(v):
    v = v & 0xF
    if v < 10:
        return chr(ord("0") + v)
    return chr(ord("A") + v - 10)


def hex8(x):
    x = x & 0xFF
    hi = (x >> 4) & 0xF
    lo = x & 0xF
    return "0x" + hex_digit(hi) + hex_digit(lo)


def pad_right(s, width):
    while len(s) < width:
        s += " "
    return s


# ============================================================
# SPI low-level
# ============================================================
def spi_transfer_byte(tx):
    rx = bytearray(1)
    txb = bytes([tx & 0xFF])

    cs.value(0)
    spi.write_readinto(txb, rx)
    cs.value(1)

    time.sleep_us(BYTE_GAP_US)
    return rx[0]


def decode_miso(rx):
    valid = (rx >> 7) & 1
    aux   = (rx >> 1) & 0b111111
    data  = rx & 1
    return valid, aux, data


def transfer(label, tx, log=True):
    rx = spi_transfer_byte(tx)

    if log:
        valid, aux, data = decode_miso(rx)

        if valid:
            state = "REPLY"
        else:
            state = "WAIT "

        print(
            pad_right(label, 18)
            + " TX=" + hex8(tx) + " " + bin8(tx)
            + "  RX=" + hex8(rx) + " " + bin8(rx)
            + "  " + state
            + " aux=" + str(aux)
            + " data=" + str(data)
        )

    return rx


# ============================================================
# ABC463B input conversion
#
# A = bit0
# B = bit1
# C = bit2
# D = bit3
# E = bit4
# ============================================================
def x_to_mask(x):
    idx = ord(x) - ord("A")

    if idx < 0 or idx >= 5:
        raise ValueError("X must be one of A, B, C, D, E")

    return 1 << idx


def s_to_mask(s):
    if len(s) != 5:
        raise ValueError("S must have length 5")

    mask = 0

    for i in range(5):
        ch = s[i]

        if ch == "o":
            mask |= 1 << i
        elif ch == "x":
            pass
        else:
            raise ValueError("S must consist of only 'o' and 'x'")

    return mask


def parse_input_text(text):
    raw_lines = text.splitlines()
    lines = []

    for line in raw_lines:
        line = line.strip()
        if line != "":
            lines.append(line)

    first = lines[0].split()
    n = int(first[0])
    x = first[1]

    ss = []
    for i in range(n):
        ss.append(lines[i + 1])

    return n, x, ss


# ============================================================
# Expected answer by RP software
# ============================================================
def expected_answer(input_text):
    n, x, ss = parse_input_text(input_text)
    idx = ord(x) - ord("A")

    for s in ss:
        if s[idx] == "o":
            return "Yes"

    return "No"


# ============================================================
# FPGA solve sequence
# ============================================================
def solve_with_fpga(input_text, log=True):
    n, x, ss = parse_input_text(input_text)

    x_mask = x_to_mask(x)

    if log:
        print("N =", n, "X =", x, "X_mask =", bin5(x_mask))
        print("---- SPI sequence ----")

    # Start sequence
    transfer("initial NOP", make_cmd(CMD_NOP), log)
    transfer("RESET", make_cmd(CMD_RESET), log)
    transfer("post RESET NOP", make_cmd(CMD_NOP), log)

    # Send X
    transfer("SET_X " + x, make_cmd(CMD_SET_X, x_mask), log)

    # Send S lines
    #
    # FPGA側は SET_S 受信時に次回MISO用 reply を準備する。
    # そのため、2個目以降の SET_S の RX に暫定REPLYが出ることがある。
    # 正式結果として採用するのは final NOP の RX だけ。
    for i in range(n):
        s = ss[i]
        s_mask = s_to_mask(s)

        if log:
            print("  S_mask", i + 1, "=", bin5(s_mask))

        transfer("SET_S " + str(i + 1) + " " + s, make_cmd(CMD_SET_S, s_mask), log)

    # Read final reply
    rx = transfer("final NOP", make_cmd(CMD_NOP), log)
    valid, aux, result = decode_miso(rx)

    if valid != 1:
        print("WARN: final NOP did not return valid REPLY")

    if result == 1:
        answer = "Yes"
    else:
        answer = "No"

    if log:
        print("---- result ----")
        print("valid =", valid, "aux =", aux, "result =", result)
        print("answer =", answer)

    # End cleanup
    transfer("end RESET", make_cmd(CMD_RESET), log)
    transfer("end NOP", make_cmd(CMD_NOP), log)

    return answer


# ============================================================
# Test cases
# ============================================================
TEST_CASES = [
    (
        "official_sample1",
        """\
3 A
xoxox
xxooo
oxxxx
""",
    ),
    (
        "official_sample2",
        """\
5 C
xoxoo
oxxoo
oxxxo
xoxxx
oxxoo
""",
    ),
    (
        "single_yes_A",
        """\
1 A
oxxxx
""",
    ),
    (
        "single_no_A",
        """\
1 A
xoooo
""",
    ),
    (
        "single_yes_E",
        """\
1 E
xxxxo
""",
    ),
    (
        "first_yes_D",
        """\
3 D
oxxox
xoxxx
ooxxx
""",
    ),
    (
        "first_yes_B",
        """\
4 B
xoxxx
xxxxx
xxxxx
xxxxx
""",
    ),
    (
        "last_yes_C",
        """\
4 C
xxxxx
oxxxx
xxoxx
xxxxx
""",
    ),
    (
        "many_yes_E",
        """\
5 E
xxxxx
xxxxo
oxxxx
xoxxx
xxoxx
""",
    ),
    (
        "all_x_no_C",
        """\
5 C
xxxxx
xxxxx
xxxxx
xxxxx
xxxxx
""",
    ),
    (
        "all_o_yes_D",
        """\
2 D
ooooo
xxxxx
""",
    ),
]


# ============================================================
# Main
# ============================================================
RUN_TESTS = True

INPUT_TEXT = """\
3 A
xoxox
xxooo
oxxxx
"""


def main():
    if USE_HW_RESET:
        print("Hardware reset")
        hw_reset()

    if RUN_TESTS:
        ok_count = 0

        for name, text in TEST_CASES:
            print()
            print("========================================")
            print("TEST:", name)
            print("========================================")

            expected = expected_answer(text)
            actual = solve_with_fpga(text, log=True)

            if actual == expected:
                ok_count += 1
                result = "PASS"
            else:
                result = "FAIL"

            print("expected =", expected, "actual =", actual, "=>", result)
            time.sleep_ms(100)

        print()
        print("========================================")
        print("SUMMARY:", ok_count, "/", len(TEST_CASES), "passed")
        print("========================================")

    else:
        ans = solve_with_fpga(INPUT_TEXT, log=True)
        print(ans)


main()