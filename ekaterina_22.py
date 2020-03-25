import threading
import time
import signal
import smbus
from datetime import datetime, timedelta
import pymssql
import serial
import RPi.GPIO as GPIO
import sqlite3

from pin_controller import PinController
from relaycontroller import RelayController
from config import system_config, logger

# import pdb; pdb.set_trace()


door_just_closed = False
can_open_the_door = False

lighting_main = False  # переменная состояния основного света
lighting_bl = False  # переменная состояния бра левый
lighting_br = False  # переменная состояния бра правый



db_connection = None


bus = smbus.SMBus(1)


# адреса контроллеров
relay1_controller = RelayController(0x38)
#relay2_controller = RelayController(0x39)

# соответствие портов контроллеров
relay1_controller.set_bit(0)  # открыть замок
relay1_controller.set_bit(1)  # закрыть замок
relay1_controller.set_bit(2)  # аварийное освещение
relay1_controller.set_bit(3)  # соленоиды
relay1_controller.set_bit(4)  # R2
relay1_controller.set_bit(5)  # R3
relay1_controller.set_bit(6)  # бра левый
relay1_controller.set_bit(7)  # бра правый

#relay2_controller.set_bit(0)  # свет спальня
#relay2_controller.set_bit(1)  # кондиционеры
#relay2_controller.set_bit(2)  # радиатор1
#relay2_controller.set_bit(3)  # радиатор2
#relay2_controller.clear_bit(4)  # зеленый
#relay2_controller.clear_bit(5)  # синий
#relay2_controller.clear_bit(6)  # красный
#relay2_controller.set_bit(7)  # резерв

data = bus.read_byte(0x38)
#data1 = bus.read_byte(0x39)

logger.info(str(bin(data)))

active_cards = []

GPIO.setmode(GPIO.BCM)


close_door_from_inside_counter = 1
open_door_counter = 1


class ProgramKilled(Exception):
    pass


# pin#26 callback (проверка сработки внут защелки (ригеля) на закрытие)
def f_lock_door_from_inside(self):
#    relay2_controller.set_bit(6)  # зажигаем красный светодиод


def f_before_lock_door_from_inside(self):
#    time.sleep(0.01)
#    if self.state:
#        relay2_controller.clear_bit(6)  # тушим красный светодиод


# pin#20 callback (проверка сработки "язычка" на открытие с последующим вызовом функции "закрытия замка")
def f_lock_latch(self):
    time.sleep(1)
    close_door()


# pin#16 callback (использование ключа)
def f_using_key(self):
#    for i in range(5):
#        relay2_controller.set_bit(4)
#        time.sleep(0.3)
#        relay2_controller.clear_bit(4)
#        relay2_controller.set_bit(5)
#        time.sleep(0.3)
#        relay2_controller.clear_bit(5)
#        relay2_controller.set_bit(6)
#        time.sleep(0.3)
#        relay2_controller.clear_bit(6)
#        time.sleep(0.5)
#    if is_door_locked_from_inside():
#        relay2_controller.set_bit(6)


# pin#19 callback (сейф)
def f_safe(self):
    pass


# pin#21 callback датчик дыма 1
def f_fire_detector1(self):
    pass


# pin#5 callback датчик дыма 2
def f_fire_detector2(self):
    pass


# pin#7 callback датчик дыма 3
def f_fire_detector3(self):
    pass


# pin#13 callback картоприемник
def f_card_key(self):
    pass


# pin#12 callback цепь автоматов
def f_circuit_breaker(self):
    pass


# pin#6 callback входная дверь
def f_door(self):
    pass


# pin#25 callback контроль наличия питания R3 (освещения)
def f_energy_sensor(self):
    pass


# pin#24 callback окно1 (балкон)
def f_window1(self):
    pass


# pin#23 callback окно2
def f_window2(self):
    pass


# pin#22 callback окно3
def f_window3(self):
    pass


# pin#27 callback выключатель основного света
def f_switch_main(self):
#    global lighting_main
#    if not lighting_main:
#        relay2_controller.clear_bit(0)
#        lighting_main = True
#    else:
#        relay2_controller.set_bit(0)
#        lighting_main = False
#  


# pin#18 callback выключатель бра левый
def f_switch_bl(self):
    global lighting_bl
    if not lighting_bl:
        relay1_controller.clear_bit(6)
        lighting_bl = True
    else:
        relay1_controller.set_bit(6)
        lighting_bl = False
  


# pin#17 callback выключатель бра правый
def f_switch_br(self):
    global lighting_br
    if not lighting_br:
        relay1_controller.clear_bit(7)
        lighting_br = True
    else:
        relay1_controller.set_bit(7)
        lighting_br = False



# pin#4 callback датчик затопления ВЩ
def f_flooding_sensor(self):
    pass


def is_door_locked_from_inside():
    time.sleep(0.1)
    return not bool(room_controller[26].state)


# закрытие замка, с предварительной проверкой
def close_door():
    global door_just_closed, can_open_the_door
    if not can_open_the_door:
        logger.info("Door is closed. Permission denied!")  # ????
        return
    relay1_controller.clear_bit(1)
    time.sleep(0.1)
    relay1_controller.set_bit(1)
    can_open_the_door = False
    door_just_closed = True

    logger.info("Client has been entered!")


def init_room():
    logger.info("Init room")
    pin_structure = {
        1: None,
        2: None,
        3: None,
        4: PinController(4, f_flooding_sensor),  # pin4  (датчик затопления ВЩ)
        5: PinController(5, f_fire_detector2),  # pin5  (датчик дыма 2)
        6: PinController(6, f_door),  # pin6  входная дверь
        7: PinController(7, f_fire_detector3),  # pin7  датчик дыма 3
        8: None,
        9: None,
        10: None,
        11: None,
        12: PinController(12, f_circuit_breaker),  # pin12 (цепь допконтактов автоматов)
        13: PinController(13, f_card_key),  # pin13 картоприемник
        14: None,
        15: None,
        16: PinController(16, f_using_key),  # pin16 (открытие замка механическим ключем)
        17: PinController(17, f_switch_br, react_on=GPIO.FALLING),  # pin17 выключатель бра правый
        18: PinController(18, f_switch_bl, react_on=GPIO.FALLING),  # pin18 выключатель бра левый
        19: PinController(19, f_safe, react_on=GPIO.FALLING),  # pin19 (сейф)
        20: PinController(20, f_lock_latch),  # pin20 ("язычка")
        21: PinController(21, f_fire_detector1),  # pin21 датчик дыма 1
        22: PinController(22, f_window2),  # pin22 (окно3)
        23: PinController(23, f_window2),  # pin23 (окно2)
        24: PinController(24, f_window1),  # pin24 (окно1-балкон)
        25: PinController(25, f_energy_sensor),  # pin25 (контроль наличия питания R3 (освещения))
        26: PinController(26, f_lock_door_from_inside, before_callback=f_before_lock_door_from_inside),  # pin26
        27: PinController(27, f_switch_main, react_on=GPIO.FALLING),  # pin27 выключатель основного света
    }

    global bus
    # todo: what is the second parameter ?
    #    lock_door_from_inside()
    logger.info("The room has been initiated")
    return pin_structure


# открытие замка с предварительной проверкой положения pin26(защелка, запрет) и последующим закрытием по таймауту
def permit_open_door():
    global door_just_closed, can_open_the_door
    if is_door_locked_from_inside():
        logger.info("The door has been locked by the guest.")

#        for i in range(5):
#            relay2_controller.set_bit(4)
#            relay2_controller.clear_bit(6)
#            time.sleep(0.1)
#            relay2_controller.set_bit(6)
#            relay2_controller.clear_bit(4)
#            time.sleep(0.1)
#
#        if not is_door_locked_from_inside():
#            relay2_controller.clear_bit(6)

        return
    relay1_controller.clear_bit(0)
    time.sleep(0.1)
    relay1_controller.set_bit(0)
    can_open_the_door = True
    for i in range(50):

        if door_just_closed:
            return

#        relay2_controller.set_bit(4)
#        time.sleep(0.1)
#        relay2_controller.clear_bit(4)
#        time.sleep(0.05)

    close_door()

    logger.info("Nobody entered")


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
    sql = "SELECT * FROM table_kluch WHERE dstart <= '{now}' AND dend >= '{now}' AND (tip = 1 OR tip = 0) AND num = {" \
          "room_number}".format(now=now, room_number=system_config.room_number)
    cursor.execute(sql)
    key_list = cursor.fetchall()
    global active_cards
    active_cards = [handle_table_row(row) for row in key_list]


def wait_rfid():
    rfid_port = serial.Serial('/dev/serial0')
    key_ = rfid_port.read(system_config.rfid_key_length)[1:11]
    logger.info("key catched {key} {datetime}".format(key=key_, datetime=datetime.utcnow()))
    return key_


def wait_rfid1():
    rfid_port = serial.Serial('/dev/ttyUSB0')
    key_ = rfid_port.read(system_config.rfid_key_length)[1:11]
    logger.info("key catched {key} {datetime}".format(key=key_, datetime=datetime.utcnow()))
    return key_


def check_pins():
    global room_controller
    pin_list_for_check = [26, 19, 21, 5, 7, 13, 12, 6, 25, 24, 23, 22, 27, 18, 17, 4]
    for item in pin_list_for_check:
        room_controller[item].check_pin()
    state_message = "Pin state : "
    for item in pin_list_for_check:
        state_message += "pin#{pin}:{state}, ".format(pin=room_controller[item].pin, state=room_controller[item].state)
    print(state_message)

    print("GPIO IN - 27, 18, 17: ", GPIO.input(27), GPIO.input(18), GPIO.input(17))


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

    room_controller = init_room()

    check_pins()
    check_pin_task = CheckPinTask(interval=timedelta(seconds=system_config.check_pin_timeout), execute=check_pins)
    check_pin_task.start()

    while True:
        try:
            logger.info("Waiting for the key")
            door_just_closed = False
            entered_key = wait_rfid()
            if entered_key in active_cards:
                logger.info("Correct key! Please enter!")
                permit_open_door()

            else:
                logger.info("Unknown key!")
#                for i in range(5):
#                    relay2_controller.set_bit(6)
#                    time.sleep(0.1)
#                    relay2_controller.clear_bit(6)
#                    time.sleep(0.05)
#                if is_door_locked_from_inside():
#                    relay2_controller.set_bit(6)
        except ProgramKilled:
            logger.info("Program killed: running cleanup code")
            card_task.stop()
            check_pin_task.stop()
            break