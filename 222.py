import threading
import time
import signal
import smbus
from datetime import datetime, timedelta
import pymssql
import serial
import RPi.GPIO as GPIO
from relaycontroller import RelayController

bus = smbus.SMBus(1)
relay2_controller = RelayController(0x39)

# relay2_controller.set_bit(4)
# relay2_controller.set_bit(5)
# relay2_controller.set_bit(6)

relay2_controller.clear_bit(4)
relay2_controller.clear_bit(5)
relay2_controller.clear_bit(6)

for i in range (500000):
    relay2_controller.set_bit(7)
    time.sleep(0.2)
    relay2_controller.clear_bit(7)
    time.sleep(0.05)
  
    relay2_controller.set_bit(6)
    time.sleep(0.2)
    relay2_controller.clear_bit(6)
    time.sleep(0.05)

    
    relay2_controller.set_bit(5)
    time.sleep(0.2)
    relay2_controller.clear_bit(5)
    time.sleep(0.05)
    
    relay2_controller.set_bit(4)
    time.sleep(0.2)
    relay2_controller.clear_bit(4)
    time.sleep(0.05)
    

data = bus.read_byte(0x38)
data1 = bus.read_byte(0x39)

print (bin (data), bin (data1))
