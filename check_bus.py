import smbus

bus = smbus.SMBus(1)

print(bin(bus.read_byte(0x38)), bin(bus.read_byte(0x39)))
