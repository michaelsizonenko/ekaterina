import time
import smbus

bus = smbus.SMBus(1)

state = str(bin(bus.read_byte(0x38))) + '  ' + str(bin(bus.read_byte(0x39)))
while True:
	tmp_state = str(bin(bus.read_byte(0x38))) + '  ' + str(bin(bus.read_byte(0x39)))
	if tmp_state != state:
		state = tmp_state
		print(state)
	time.sleep(0.1)
