from machine import Pin, SPI
import time


PIN_MISO = 0
PIN_SS   = 1
PIN_SCK  = 2
PIN_MOSI = 3
PIN_RST  = 14

SPI_BAUDRATE = 250_000

CMD_MOSI_NOP   = 0b00
CMD_MOSI_DATA  = 0b01
CMD_MOSI_START = 0b10

CMD_MISO_WAIT = 0b00
CMD_MISO_DATA = 0b01
CMD_MISO_DONE = 0b11


spi = SPI(
    0,
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


def xfer(value):
    tx = bytearray([value & 0xFF])
    rx = bytearray(1)
    ss.value(0)
    spi.write_readinto(tx, rx)
    ss.value(1)
    time.sleep_us(20)
    return rx[0]


def hw_reset():
    rst_n.value(0)
    time.sleep_ms(2)
    rst_n.value(1)
    time.sleep_ms(2)


def read_20_lines(max_nop=500):
    lines = []
    current = []

    for _ in range(max_nop):
        status, eol, data = parse_miso(xfer(make_cmd(CMD_MOSI_NOP)))

        if status == CMD_MISO_WAIT:
            continue

        if status == CMD_MISO_DATA:
            current.append(data)
            if eol:
                lines.append(current)
                current = []
                if len(lines) >= 20:
                    return lines
            continue

        if status == CMD_MISO_DONE:
            break

    return lines


def line_text(line):
    return " ".join(str(x) for x in line)


def run_with_prefix_nops(prefix_nops):
    hw_reset()

    for _ in range(prefix_nops):
        xfer(make_cmd(CMD_MOSI_NOP))

    # giver 1 -> receiver 2
    xfer(make_cmd(CMD_MOSI_DATA, done=1, data=2))
    xfer(make_cmd(CMD_MOSI_START))

    lines = read_20_lines()

    r1 = lines[0] if len(lines) > 0 else []
    r2 = lines[1] if len(lines) > 1 else []
    r3 = lines[2] if len(lines) > 2 else []
    r4 = lines[3] if len(lines) > 3 else []

    print(
        "prefix_nops={} -> r1=[{}] r2=[{}] r3=[{}] r4=[{}]".format(
            prefix_nops,
            line_text(r1),
            line_text(r2),
            line_text(r3),
            line_text(r4),
        )
    )


def main():
    print("Entry probe: giver 1 -> receiver 2")
    print("Expected when ST_INPUT is ready: r1=[0] r2=[1 1] r3=[0] r4=[0]")
    print("")

    for prefix_nops in range(0, 8):
        run_with_prefix_nops(prefix_nops)


main()
