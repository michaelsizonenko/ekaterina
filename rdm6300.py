import serial

key_length = 14

try:
    rfid_port = serial.Serial('/dev/serial0')
#    rfid_port = serial.Serial('/dev/ttyAMA0', 9600)
    print(rfid_port)
#    key = rfid_port.read()
    key = rfid_port.read(key_length)[1:11]
    print(key)
    print("Finished execution")
except KeyboardInterrupt as e:
    print("Bye")
except Exception as e:
    print(e)
finally:
    pass
