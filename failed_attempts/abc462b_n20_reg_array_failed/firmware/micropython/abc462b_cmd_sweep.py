from machine import Pin, SPI
import time


PIN_MISO = 0
PIN_SS   = 1
PIN_SCK  = 2
PIN_MOSI = 3
PIN_RST  = 14

SPI_BAUDRATE = 250_000

CMD_NOMINAL_NOP = 0

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


def hw_reset_to_input():
    rst_n.value(0)
    time.sleep_ms(2)
    rst_n.value(1)
    time.sleep_ms(2)
    xfer(make_cmd(CMD_NOMINAL_NOP))
    time.sleep_ms(1)


def read_lines(max_nop=80):
    lines = []
    current = []

    for _ in range(max_nop):
        status, eol, data = parse_miso(xfer(make_cmd(CMD_NOMINAL_NOP)))

        if status == CMD_MISO_WAIT:
            continue

        if status == CMD_MISO_DATA:
            current.append(data)
            if eol:
                lines.append(current)
                current = []
                if len(lines) >= 4:
                    break
            continue

        if status == CMD_MISO_DONE:
            break

    return lines


def line_text(line):
    return " ".join(str(x) for x in line)


def main():
    print("Trying one logical input: giver 1 -> receiver 2")
    print("Expected first 4 receiver lines, if command pair is correct:")
    print("  r1: 0")
    print("  r2: 1 1")
    print("  r3: 0")
    print("  r4: 0")
    print("")

    for data_cmd in range(4):
        for start_cmd in range(4):
            if data_cmd == CMD_NOMINAL_NOP:
                continue
            if start_cmd == CMD_NOMINAL_NOP:
                continue

            hw_reset_to_input()
            xfer(make_cmd(data_cmd, done=1, data=2))
            xfer(make_cmd(start_cmd))
            lines = read_lines()

            interesting = False
            for line in lines:
                if line != [0]:
                    interesting = True

            if interesting or (data_cmd == 1 and start_cmd == 2):
                print(
                    "data_cmd={} start_cmd={} -> {}".format(
                        data_cmd,
                        start_cmd,
                        " | ".join(line_text(line) for line in lines),
                    )
                )


main()
