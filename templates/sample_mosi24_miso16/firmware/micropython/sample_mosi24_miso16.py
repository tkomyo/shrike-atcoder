# abc463c_test_a_spi_echo.py

from machine import Pin, SPI
import time


SPI_ID = 0

PIN_MISO = 0
PIN_SS   = 1
PIN_SCK  = 2
PIN_MOSI = 3
PIN_RST  = 14

BAUDRATE = 1_000_000


spi = SPI(
    SPI_ID,
    baudrate=BAUDRATE,
    polarity=0,
    phase=0,
    bits=8,
    firstbit=SPI.MSB,
    sck=Pin(PIN_SCK),
    mosi=Pin(PIN_MOSI),
    miso=Pin(PIN_MISO),
)

cs = Pin(PIN_SS, Pin.OUT, value=1)
fpga_rst = Pin(PIN_RST, Pin.OUT, value=1)


RSP_OK = 0b010


def xfer_byte(tx):
    rx = bytearray(1)

    cs.value(0)
    time.sleep_us(2)
    spi.write_readinto(bytes([tx & 0xFF]), rx)
    time.sleep_us(2)
    cs.value(1)
    time.sleep_us(20)

    return rx[0]


def fpga_reset_pulse():
    cs.value(1)
    fpga_rst.value(0)
    time.sleep_ms(5)
    fpga_rst.value(1)
    time.sleep_ms(20)


def make_mosi_bytes(cmd, data, cmd_aux=0, idx=0, aux=0):
    cmd &= 0x7
    cmd_aux &= 0x1
    idx &= 0xF
    aux &= 0x3F
    data &= 0x3FF

    b0 = (cmd << 5) | (cmd_aux << 4) | idx
    b1 = (aux << 2) | ((data >> 8) & 0x03)
    b2 = data & 0xFF

    return b0, b1, b2


def send_frame_get_reply(cmd, data, cmd_aux=0, idx=0, aux=0):
    b0, b1, b2 = make_mosi_bytes(cmd, data, cmd_aux, idx, aux)

    # MOSI 3 bytes
    r0 = xfer_byte(b0)
    r1 = xfer_byte(b1)
    r2 = xfer_byte(b2)

    # MISO 2 bytes, sent during dummy bytes
    hi = xfer_byte(0x00)
    lo = xfer_byte(0x00)

    reply = (hi << 8) | lo

    rsp = (reply >> 13) & 0x7
    cmd_echo = (reply >> 10) & 0x7
    data_echo = reply & 0x3FF

    return {
        "mosi": (b0, b1, b2),
        "pre_rx": (r0, r1, r2),
        "reply_raw": (hi, lo),
        "reply": reply,
        "rsp": rsp,
        "cmd_echo": cmd_echo,
        "data_echo": data_echo,
    }


def check(label, cmd, data, idx=0, aux=0):
    r = send_frame_get_reply(cmd=cmd, data=data, idx=idx, aux=aux)

    ok = (
        r["rsp"] == RSP_OK and
        r["cmd_echo"] == (cmd & 0x7) and
        r["data_echo"] == (data & 0x3FF)
    )

    status = "PASS" if ok else "FAIL"

    b0, b1, b2 = r["mosi"]
    pr0, pr1, pr2 = r["pre_rx"]
    hi, lo = r["reply_raw"]

    print(
        "{:<24} {}  CMD={} DATA=0x{:03X}  "
        "MOSI=[{:02X} {:02X} {:02X}] preRX=[{:02X} {:02X} {:02X}] "
        "MISO=[{:02X} {:02X}] RSP={} CMD_ECHO={} DATA_ECHO=0x{:03X}"
        .format(
            label,
            status,
            cmd,
            data & 0x3FF,
            b0, b1, b2,
            pr0, pr1, pr2,
            hi, lo,
            r["rsp"],
            r["cmd_echo"],
            r["data_echo"],
        )
    )

    return ok


def main():
    print("ABC463C Test_A: SPI 3-byte MOSI / 2-byte MISO echo")
    print("SPI{} baudrate={}".format(SPI_ID, BAUDRATE))

    fpga_reset_pulse()

    fail = 0

    tests = [
        ("zero",      0b000, 0x000),
        ("one",       0b001, 0x001),
        ("pattern",   0b010, 0x2A5),
        ("max",       0b011, 0x3FF),
        ("alt",       0b101, 0x155),
        ("reset-cmd", 0b111, 0x0C3),
    ]

    print("\n===== SPI echo tests =====")

    for label, cmd, data in tests:
        if not check(label, cmd, data):
            fail += 1

    print("\n===== RESULT =====")
    if fail == 0:
        print("ALL PASS")
    else:
        print("FAIL count =", fail)


main()