import smbus
import time
import sys

bus = smbus.SMBus(1)
bus.write_byte_data(0x38, 0x02, 0xff)

bus.write_byte_data(0x39, 0x06, 0xff)
# time.sleep(0.5)

# cycles = int(sys.argv[1])
b = 0.1
for x in range(0, 10):

    bus.write_byte_data(0x38, 0x09, 0xfe)
    time.sleep(b)
    bus.write_byte_data(0x38, 0x09, 0xfd)
    time.sleep(b)
    bus.write_byte_data(0x38, 0x09, 0xfb)
    time.sleep(b)
    bus.write_byte_data(0x38, 0x09, 0xf7)
    time.sleep(b)
    bus.write_byte_data(0x38, 0x09, 0xef)
    time.sleep(b)
    bus.write_byte_data(0x38, 0x09, 0xdf)
    time.sleep(b)
    bus.write_byte_data(0x38, 0x09, 0xbf)
    time.sleep(b)
    bus.write_byte_data(0x38, 0x09, 0x7f)
    time.sleep(b)
    bus.write_byte_data(0x38, 0x09, 0xff)

    bus.write_byte_data(0x39, 0x06, 0xfe)
    time.sleep(b)
    bus.write_byte_data(0x39, 0x06, 0xfd)
    time.sleep(b)
    bus.write_byte_data(0x39, 0x06, 0xfb)
    time.sleep(b)
    bus.write_byte_data(0x39, 0x06, 0xf7)
    time.sleep(b)
    bus.write_byte_data(0x39, 0x06, 0xff)
    # time.sleep(0.5)
