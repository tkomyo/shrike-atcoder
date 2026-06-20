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


def hw_reset_to_input():
    rst_n.value(0)
    time.sleep_ms(2)
    rst_n.value(1)
    time.sleep_ms(2)
    xfer(make_cmd(CMD_MOSI_NOP))
    time.sleep_ms(1)


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


def run_one(label, data_bytes):
    hw_reset_to_input()

    for value in data_bytes:
        xfer(value)

    xfer(make_cmd(CMD_MOSI_START))
    lines = read_20_lines()

    hits = []
    for i, line in enumerate(lines):
        if line != [0]:
            hits.append((i + 1, line))

    print(label)
    if hits:
        for receiver, line in hits:
            print("  receiver {}: {}".format(receiver, line_text(line)))
    else:
        print("  no hit")


def main():
    print("DATA probe")
    print("Expected for ordinary DATA done=1 data=2:")
    print("  receiver 2: 1 1")
    print("")

    run_one(
        "single DATA done=1 data=2",
        [make_cmd(CMD_MOSI_DATA, done=1, data=2)],
    )

    run_one(
        "single DATA done=0 data=2",
        [make_cmd(CMD_MOSI_DATA, done=0, data=2)],
    )

    run_one(
        "DATA done=0 data=2, then DATA done=1 data=0",
        [
            make_cmd(CMD_MOSI_DATA, done=0, data=2),
            make_cmd(CMD_MOSI_DATA, done=1, data=0),
        ],
    )

    print("")
    print("payload sweep: one DATA done=1 data=1..20")
    for data in range(1, 21):
        run_one(
            "payload data={}".format(data),
            [make_cmd(CMD_MOSI_DATA, done=1, data=data)],
        )


main()
