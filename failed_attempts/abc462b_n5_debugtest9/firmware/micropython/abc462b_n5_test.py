from machine import Pin, SPI
import time


# Shrike-Lite RP2040 <-> FPGA SPI pins
PIN_MISO = 0
PIN_SS   = 1
PIN_SCK  = 2
PIN_MOSI = 3
PIN_RST  = 14

SPI_ID = 0
SPI_BAUDRATE = 1_000_000

N_FPGA = 5


# MOSI command format:
#   [7:6] : command
#   [5]   : DONE flag
#   [4:0] : data
CMD_MOSI_NOP   = 0b00
CMD_MOSI_DATA  = 0b01
CMD_MOSI_START = 0b10
CMD_MOSI_RESET = 0b11


# MISO format:
#   [7:6] : status
#   [5]   : EOL flag
#   [4:0] : data
CMD_MISO_WAIT = 0b00
CMD_MISO_DATA = 0b01
CMD_MISO_DONE = 0b11


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

ss = Pin(PIN_SS, Pin.OUT, value=1)
rst_n = Pin(PIN_RST, Pin.OUT, value=1)


def make_cmd(cmd, done=0, data=0):
    return ((cmd & 0x03) << 6) | ((done & 0x01) << 5) | (data & 0x1F)


def parse_miso(value):
    return (value >> 6) & 0x03, (value >> 5) & 0x01, value & 0x1F


def spi_xfer(value):
    tx = bytearray([value & 0xFF])
    rx = bytearray(1)
    ss.value(0)
    spi.write_readinto(tx, rx)
    ss.value(1)
    time.sleep_us(20)
    return rx[0]


def fpga_hw_reset():
    rst_n.value(0)
    time.sleep_ms(2)
    rst_n.value(1)
    time.sleep_ms(2)

    # The Verilog starts in ST_INIT. One SPI byte is needed to move it to ST_INPUT.
    spi_xfer(make_cmd(CMD_MOSI_NOP))
    time.sleep_ms(1)


def fpga_soft_reset():
    # If the FPGA is in ST_DONE/ST_REPLY/ST_INPUT, RESET moves it to ST_INIT.
    spi_xfer(make_cmd(CMD_MOSI_RESET))

    # Then one more byte lets ST_INIT clear registers and enter ST_INPUT.
    spi_xfer(make_cmd(CMD_MOSI_NOP))
    time.sleep_ms(1)


def send_giver_line(recipients):
    if len(recipients) == 0:
        spi_xfer(make_cmd(CMD_MOSI_DATA, done=1, data=0))
        return

    for i, receiver in enumerate(recipients):
        done = 1 if i == len(recipients) - 1 else 0
        spi_xfer(make_cmd(CMD_MOSI_DATA, done=done, data=receiver))


def send_case(lines):
    for recipients in lines:
        send_giver_line(recipients)

    spi_xfer(make_cmd(CMD_MOSI_START))


def read_reply_lines(max_lines=N_FPGA, max_nop=1000):
    lines = []
    current = []

    for _ in range(max_nop):
        value = spi_xfer(make_cmd(CMD_MOSI_NOP))
        status, eol, data = parse_miso(value)

        if status == CMD_MISO_WAIT:
            continue

        if status == CMD_MISO_DATA:
            current.append(data)
            if eol:
                lines.append(current)
                current = []
                if len(lines) >= max_lines:
                    return lines
            continue

        if status == CMD_MISO_DONE:
            break

        raise RuntimeError("unknown MISO status: {}".format(status))

    raise RuntimeError("reply timeout: got {} lines".format(len(lines)))


def drain_done(max_nop=20):
    for _ in range(max_nop):
        value = spi_xfer(make_cmd(CMD_MOSI_NOP))
        status, _, _ = parse_miso(value)
        if status == CMD_MISO_DONE:
            return True
    return False


def expected_lines(lines):
    hits = [set() for _ in range(N_FPGA)]

    for giver_idx, recipients in enumerate(lines):
        giver_id = giver_idx + 1
        for receiver_id in recipients:
            if 1 <= receiver_id <= N_FPGA:
                hits[receiver_id - 1].add(giver_id)

    result = []
    for receiver_idx in range(N_FPGA):
        givers = sorted(hits[receiver_idx])
        if len(givers) == 0:
            result.append([0])
        else:
            result.append([len(givers)] + givers)

    return result


def line_to_text(line):
    return " ".join(str(x) for x in line)


def print_case_input(lines):
    print(len(lines))
    for recipients in lines:
        print("{} {}".format(len(recipients), line_to_text(recipients)).rstrip())


def run_one_case(name, lines, use_hw_reset=False):
    if len(lines) != N_FPGA:
        raise ValueError("N=5 test requires exactly {} giver lines".format(N_FPGA))

    print("")
    print("===== {} =====".format(name))
    print("[input]")
    print_case_input(lines)

    if use_hw_reset:
        fpga_hw_reset()
    else:
        fpga_soft_reset()

    send_case(lines)
    actual = read_reply_lines(N_FPGA)
    drain_done()

    expected = expected_lines(lines)

    print("[fpga output]")
    for line in actual:
        print(line_to_text(line))

    if actual == expected:
        print("PASS")
    else:
        print("FAIL")
        print("[expected]")
        for line in expected:
            print(line_to_text(line))


TEST_CASES = [
    (
        "AtCoder sample 1 plus empty receiver 5",
        [
            [2],
            [3],
            [2],
            [1, 2, 3],
            [],
        ],
    ),
    (
        "AtCoder sample 2 plus empty receiver 5",
        [
            [2, 3, 4],
            [1, 4],
            [1, 2],
            [2, 3],
            [],
        ],
    ),
    (
        "Boundary giver 5 and receiver 5",
        [
            [5],
            [5],
            [5],
            [5],
            [1, 2, 3, 4, 5],
        ],
    ),
    (
        "Self gift and duplicate gift",
        [
            [1, 1, 2, 2, 3],
            [2, 2, 2],
            [1, 3, 3, 5],
            [4, 4],
            [5, 5, 1, 1],
        ],
    ),
    (
        "All empty",
        [
            [],
            [],
            [],
            [],
            [],
        ],
    ),
]


def main():
    fpga_hw_reset()

    first = True
    for name, lines in TEST_CASES:
        run_one_case(name, lines, use_hw_reset=first)
        first = False

    print("")
    print("All tests finished.")


main()
