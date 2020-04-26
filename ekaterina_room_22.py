import threading
import time
import signal
import smbus
from datetime import datetime, timedelta
import pymssql
import serial
import RPi.GPIO as GPIO
import sqlite3
import asyncio
import socket

from pin_controller import PinController
from relaycontroller import RelayController
from config import system_config, logger

# import pdb; pdb.set_trace()


door_just_closed = False
domofon = False

db_connection = None

bus = smbus.SMBus(1)

# адреса контроллеров
relay1_controller = RelayController(0x38)

# соответствие портов контроллеров
relay1_controller.set_bit(0)  # открыть замок
relay1_controller.set_bit(1)  # закрыть замок
relay1_controller.set_bit(2)  # "дверь открыта"

data = bus.read_byte(0x38)

logger.info(str(bin(data)))

active_cards = []

GPIO.setmode(GPIO.BCM)

close_door_from_inside_counter = 1
open_door_counter = 1


class ProgramKilled(Exception):
    pass


# pin#26 callback (проверка сработки внут защелки (ригеля) на закрытие)
async def f_lock_door_from_inside(self):
    pass


def f_before_lock_door_from_inside(self):
    pass


# pin#12 callback (проверка сработки "язычка" на открытие с последующим вызовом функции "закрытия замка")
async def f_lock_latch(self):
    logger.info("воспользовались ручкой замка, замок будет закрыт")
    await asyncio.sleep(0.3)
    await close_door()


# pin#16 callback (использование ключа)
async def f_using_key(self):
    pass


# pin#25 callback (knopki)
async def f_knopki(self):
    logger.info("Открытие кнопками замка")
    await permit_open_door()


# pin#21 callback domofon 1
async def f_domofon(self):
    global domofon
    domofon = True
    logger.info("Открытие домофоном")
    await permit_open_door()


# pin#6 callback входная дверь
async def f_door(self):
    pass


async def is_door_locked_from_inside():
    await asyncio.sleep(0.1)
    return not bool(room_controller[26].state)


def init_room(loop):
    logger.info("Init room")
    pin_structure = {
        1: None,
        2: None,
        3: None,
        4: None,
        5: None,
        6: PinController(loop, 6, f_door),  # pin6  входная дверь
        7: None,
        8: None,
        9: None,
        10: None,
        11: None,
        12: PinController(loop, 12, f_lock_latch),  # pin12 ("язычка")
        13: None,
        14: None,
        15: None,
        16: PinController(loop, 16, f_using_key),  # pin16 (открытие замка механическим ключем)
        17: None,
        18: None,
        19: None,
        20: None,
        21: PinController(loop, 21, f_domofon),  # pin21 domofon /, up_down=GPIO.PUD_DOWN, react_on=GPIO.FALLING /
        22: None,
        23: None,
        24: None,
        25: PinController(loop, 25, f_knopki),  # pin25 (f_knopki)
        26: PinController(loop, 26, f_lock_door_from_inside, before_callback=f_before_lock_door_from_inside),  # pin26
        27: None,
    }

    global bus
    # todo: what is the second parameter ?
    #    lock_door_from_inside()
    logger.info("The room has been initiated")
    return pin_structure


# открытие замка с предварительной проверкой положения pin26(защелка, запрет) и последующим закрытием по таймауту
async def permit_open_door():
    global door_just_closed, domofon
    if await is_door_locked_from_inside():
        logger.info("The door has been locked by the guest.")
        return

    if not door_just_closed:
        logger.info("Комманда открытия заблокирована. Замок не закрыт")
        return
    relay1_controller.clear_bit(0)
    await asyncio.sleep(0.15)
    relay1_controller.set_bit(0)
    door_just_closed = False

    if not domofon:
        relay1_controller.clear_bit(2)
        await asyncio.sleep(0.2)
        relay1_controller.set_bit(2)
    domofon = False
    for i in range(500):
        if door_just_closed:
            return
        await asyncio.sleep(0.01)

    logger.info("дверь не открывали, замок будет закрыт по таймауту")
    await close_door()


# закрытие замка, с предварительной проверкой
async def close_door():
    global door_just_closed
    if door_just_closed:
        logger.info("Комманда закрытия заблокирована. Замок уже закрыт")
        return

    relay1_controller.clear_bit(1)
    await asyncio.sleep(0.2)
    relay1_controller.set_bit(1)
    door_just_closed = True
    logger.info("Замок закрыт")


def handle_table_row(row_):
    return row_[system_config.rfig_key_table_index].replace(" ", "").encode("UTF-8")


def get_db_connection():
    global db_connection
    if db_connection is None:
        db_connection = pymssql.connect(**system_config.db_config.__dict__)
    return db_connection


def get_active_cards():
    cursor = get_db_connection().cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    sql = "SELECT * FROM table_kluch WHERE dstart <= '{now}' AND dend >= '{now}' AND num = {" \
          "room_number}".format(now=now, room_number=system_config.room_number)
    cursor.execute(sql)
    key_list = cursor.fetchall()
    print(key_list)
    global active_cards
    active_cards = [handle_table_row(row) for row in key_list]


def wait_rfid0():
    rfid_port = serial.Serial('/dev/serial0')
    key_ = rfid_port.read(system_config.rfid_key_length)[1:11]
    logger.info("key catched {key} {datetime}".format(key=key_, datetime=datetime.utcnow()))
    return key_


def wait_rfid1():
    rfid_port = serial.Serial('/dev/ttyUSB0')
    key_ = rfid_port.read(system_config.rfid_key_length)[1:11]
    logger.info("key catched {key} {datetime}".format(key=key_, datetime=datetime.utcnow()))
    return key_


def wait_rfid():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect(('192.168.9.43', 9763))
    result = sock.recv(1024)
    key1_ = result.hex()[2:12]
    key2_ = key1_.upper()
    key_ = key2_.encode('utf-8')
    print(key_)
    logger.info("key catched {key} {datetime}".format(key=key_, datetime=datetime.utcnow()))
    return key_


def check_pins():
    global room_controller
    pin_list_for_check = [6, 12, 16, 21, 25, 26]
    for item in pin_list_for_check:
        room_controller[item].check_pin()
    state_message = "Pin state : "
    for item in pin_list_for_check:
        state_message += "pin#{pin}:{state}, ".format(pin=room_controller[item].pin, state=room_controller[item].state)
    print(state_message)


def signal_handler(signum, frame):
    raise ProgramKilled


class CheckPinTask(threading.Thread):

    def __init__(self, interval, execute):
        threading.Thread.__init__(self)
        self.daemon = False
        self.stopped = threading.Event()
        self.interval = interval
        self.execute = execute

    def stop(self):
        self.stopped.set()
        self.join()

    def run(self):
        while not self.stopped.wait(self.interval.total_seconds()):
            self.execute()


class CheckActiveCardsTask(threading.Thread):
    def __init__(self, interval, execute, *args, **kwargs):
        threading.Thread.__init__(self)
        self.daemon = False
        self.stopped = threading.Event()
        self.interval = interval
        self.execute = execute
        self.args = args
        self.kwargs = kwargs

    def stop(self):
        self.stopped.set()
        self.join()

    def run(self):
        while not self.stopped.wait(self.interval.total_seconds()):
            self.execute(*self.args, **self.kwargs)


if __name__ == "__main__":
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    get_active_cards()
    card_task = CheckActiveCardsTask(interval=timedelta(seconds=system_config.new_key_check_interval),
                                     execute=get_active_cards)
    card_task.start()

    loop = asyncio.get_event_loop()
    room_controller = init_room(loop)

    check_pins()
    check_pin_task = CheckPinTask(interval=timedelta(seconds=system_config.check_pin_timeout), execute=check_pins)
    check_pin_task.start()
    close_door()

    loop.run_forever()
    loop.close()
    # while True:
    #     if f_lock_latch:
    #         close_door()
    #     try:
    #         logger.info("Waiting for the key")
    #         entered_key = wait_rfid()
    #
    #         if entered_key in active_cards:
    #             logger.info("Correct key! Please enter!")
    #             permit_open_door()
    #
    #         else:
    #             logger.info("Unknown key!")
    #     #
    #     except ProgramKilled:
    #         logger.info("Program killed: running cleanup code")
    #         card_task.stop()
    #         check_pin_task.stop()
    #         break
