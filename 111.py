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

data = bus.read_byte(0x38)
data1 = bus.read_byte(0x39)

print (bin (data), bin (data1))
