import RPi.GPIO as GPIO  # Импортируем библиотеку по работе с GPIO
import time
import os  # Импортируем класс для работы со временем
import sys
import traceback  # Импортируем библиотеки для обработки исключений
import smbus
import datetime
import socket

os.system("clear")
bus = smbus.SMBus(1)
# sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
# sock.connect(('192.168.9.44', 9761))
# result = sock.recv(1024)
# print(result.hex())

# try:
# === Инициализация пинов ===
GPIO.setmode(GPIO.BCM)
pinBT17 = 17
pinBT18 = 18
pinBT27 = 27

GPIO.setup([pinBT17, pinBT18, pinBT27], GPIO.IN,
           pull_up_down=GPIO.PUD_DOWN)  # назначаем пины "входами" и подтягиваем их к

i2cplate38 = 0b11111111  # задаем значение "все выключено" для первой платы расширения с адресом 0х38
i2cplate39 = 0b11111111  # задаем значение "все выключено" для второй платы расширения с адресом 0х39

# выключаем все реле
bus.write_byte_data(0x38, 0xFF, i2cplate38)
bus.write_byte_data(0x39, 0xff, i2cplate39)

# while 1:

cmd38_7 = 1  # k7  /Бра L в спальной 1
cmd38_8 = 1  # k8  /Бра R в спальной 1
cmd39_1 = 1  # k9  /Основной свет в спальной 1

pin17 = 17
pin18 = 18
pin27 = 27

apin17 = 1
apin18 = 1
apin27 = 1


def callback_func(pin):
    # result = sock.recv(1024)
    # print(result.hex())
    global apin17
    global apin18
    global apin27

    global cmd38_7
    global cmd38_8
    global cmd39_1

    global i2cplate38
    global i2cplate39

    pin17 = 17
    pin18 = 18
    pin27 = 27

    GPIO.setup([pin17, pin18, pin27], GPIO.IN,
               pull_up_down=GPIO.PUD_DOWN)  # назначаем пины "входами" и подтягиваем их к 0
    r = 0
    while r < 1:
        pinBTN17 = GPIO.input(pin17)
        pinBTN18 = GPIO.input(pin18)
        pinBTN27 = GPIO.input(pin27)

        time.sleep(0.01)
        r += 1
        print(r)

        if apin27 and not pinBTN27:
            time.sleep(0.01)
            pinBTN27 = GPIO.input(pin27)
            if apin27 and not pinBTN27:
                cmd39_1 *= -1
                if cmd39_1 == -1:
                    i2cplate39 = (i2cplate39 & 0b11111110)
                    print(datetime.datetime.today(), "vkl osnov")
                if cmd39_1 == 1:
                    i2cplate39 = (i2cplate39 | 0b1)
                    print(datetime.datetime.today(), "otkl osnov")
                bus.write_byte_data(0x39, 0xff, i2cplate39)
                time.sleep(0.1)
        apin27 = pinBTN27

        if apin17 and not pinBTN17:
            time.sleep(0.01)
            if apin17 and not pinBTN17:
                cmd38_7 *= -1
                if cmd38_7 == -1:
                    i2cplate38 = (i2cplate38 & 0b10111111)
                    print(datetime.datetime.today(), "vkl BR.R")
                if cmd38_7 == 1:
                    i2cplate38 = (i2cplate38 | 0b01000000)
                    print(datetime.datetime.today(), "otkl BR.R")
                bus.write_byte_data(0x38, 0xff, i2cplate38)
                time.sleep(0.1)
        apin17 = pinBTN17

        if apin18 and not pinBTN18:
            cmd38_8 *= -1
            if cmd38_8 == -1:
                i2cplate38 = (i2cplate38 & 0b01111111)
                print(datetime.datetime.today(), "vkl BR.L")
            if cmd38_8 == 1:
                i2cplate38 = (i2cplate38 | 0b10000000)
                print(datetime.datetime.today(), "otkl BR.L")
            bus.write_byte_data(0x38, 0xff, i2cplate38)
            time.sleep(0.1)
        apin18 = pinBTN18


GPIO.add_event_detect(pin17, GPIO.FALLING, callback=callback_func)
GPIO.add_event_detect(pin18, GPIO.FALLING, callback=callback_func)
GPIO.add_event_detect(pin27, GPIO.FALLING, callback=callback_func)

# print(result.hex())
# time.sleep(1)
