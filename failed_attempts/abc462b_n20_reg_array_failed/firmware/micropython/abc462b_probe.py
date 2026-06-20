from machine import Pin, SPI
import time


PIN_MISO = 0
PIN_SS   = 1
PIN_SCK  = 2
PIN_MOSI = 3
PIN_RST  = 14

SPI_ID = 0
SPI_BAUDRATE = 250_000

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


def spi_xfer(value, label=""):
    tx = bytearray([value & 0xFF])
    rx = bytearray(1)
    ss.value(0)
    spi.write_readinto(tx, rx)
    ss.value(1)
    time.sleep_us(20)

    status, eol, data = parse_miso(rx[0])
    print(
        "{:<18} TX=0x{:02X} RX=0x{:02X} stat={} eol={} data={}".format(
            label,
            tx[0],
            rx[0],
            status,
            eol,
            data,
        )
    )
    return rx[0]


def hw_reset():
    rst_n.value(0)
    time.sleep_ms(2)
    rst_n.value(1)
    time.sleep_ms(2)


def enter_input(cmd_nop):
    # One byte is needed to move Verilog ST_INIT -> ST_INPUT.
    spi_xfer(make_cmd(cmd_nop), "enter input")
    time.sleep_ms(1)


def soft_reset(cmd_reset, cmd_nop):
    spi_xfer(make_cmd(cmd_reset), "soft reset")
    spi_xfer(make_cmd(cmd_nop), "enter input")
    time.sleep_ms(1)


def read_some(cmd_nop, count, title):
    print(title)
    for i in range(count):
        spi_xfer(make_cmd(cmd_nop), "read {}".format(i + 1))


def probe_protocol(name, cmd_nop, cmd_data, cmd_start, cmd_reset):
    print("")
    print("===== {} =====".format(name))
    print("cmd_nop={} cmd_data={} cmd_start={} cmd_reset={}".format(
        cmd_nop,
        cmd_data,
        cmd_start,
        cmd_reset,
    ))

    soft_reset(cmd_reset, cmd_nop)

    # Give member 1 -> receiver 2.
    # If DATA is interpreted correctly, NOPs before START should remain WAIT.
    # If DATA is actually interpreted as START, these NOPs will already begin reply.
    spi_xfer(make_cmd(cmd_data, done=1, data=2), "data rcv=2 done")
    read_some(cmd_nop, 5, "[before explicit START]")

    spi_xfer(make_cmd(cmd_start), "start")
    read_some(cmd_nop, 12, "[after explicit START]")


def main():
    hw_reset()
    enter_input(0b00)

    # Expected mapping from the current top.v:
    #   NOP=00, DATA=01, START=10, RESET=11
    probe_protocol("A: expected top.v mapping", 0b00, 0b01, 0b10, 0b11)

    # Diagnostic swapped mapping:
    #   NOP=00, DATA=10, START=01, RESET=11
    # If this one works better, DATA/START constants differ from the Python script.
    probe_protocol("B: DATA/START swapped", 0b00, 0b10, 0b01, 0b11)


main()
