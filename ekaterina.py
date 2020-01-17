import threading
import time
import signal
import smbus
from datetime import datetime, timedelta
import pymssql
import serial
import RPi.GPIO as GPIO

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
print("lighting_bl:   ", lighting_bl)
print("lighting_br:   ", lighting_br)
print("lighting_main: ", lighting_main)

bus = smbus.SMBus(1)

# соответствие пинов
doors_lock_pin = 26  # защелка запрет (заперто изнутри)
lock_latch_pin = 20  # сработка язычка замка
using_key_pin = 16  # использование ключа
safe_pin = 19  # сейф
fire_detector1_pin = 21  # датчик дыма 1
fire_detector2_pin = 5  # датчик дыма 2
fire_detector3_pin = 7  # датчик дыма 3
card_key_pin = 13  # картоприемник
circuit_breaker_pin = 12  # цепь автоматов
door_pin = 6  # входная дверь
energy_sensor_pin = 25  # контроль наличия питания R3 (освещения)
window1_pin = 24  # окно 1 (балкон)
window2_pin = 23  # окно 2
window3_pin = 22  # окно 3
switch_main_pin = 27  # выключатель свет в спальне
switch_bl_pin = 18  # выключатель бра левый
switch_br_pin = 17  # выключатель бра правый
flooding_sensor_pin = 4  # датчик затопления ВЩ

# адреса контроллеров
relay1_controller = RelayController(0x38)
relay2_controller = RelayController(0x39)

# соответствие портов контроллеров
relay1_controller.set_bit(0)  # открыть замок
relay1_controller.set_bit(1)  # закрыть замок
relay1_controller.set_bit(2)  # аварийное освещение
relay1_controller.set_bit(3)  # соленоиды
relay1_controller.set_bit(4)  # R2
relay1_controller.set_bit(5)  # R3
relay1_controller.set_bit(6)  # бра левый
relay1_controller.set_bit(7)  # бра правый

relay2_controller.set_bit(0)  # свет спальня
relay2_controller.set_bit(1)  # кондиционеры
relay2_controller.set_bit(2)  # радиатор1
relay2_controller.set_bit(3)  # радиатор2
relay2_controller.clear_bit(4)  # зеленый
relay2_controller.clear_bit(5)  # синий
relay2_controller.clear_bit(6)  # красный
relay2_controller.set_bit(7)  # резерв

data = bus.read_byte(0x38)
data1 = bus.read_byte(0x39)

logger.info(str(bin(data) + " " + bin(data1)))

active_cards = []

GPIO.setmode(GPIO.BCM)

# переменные состояния пинов
doors_lock_pin26_state = 1  # защелка запрет (заперто изнутри)
lock_latch_pin20_state = 1  # сработка язычка замка
using_key_pin16_state = 1  # использование ключа
safe_pin19_state = 1  # сейф
fire_detector1_pin21_state = 1  # датчик дыма 1
fire_detector2_pin5_state = 1  # датчик дыма 2
fire_detector3_pin7_state = 1  # датчик дыма 3
card_key_pin13_state = 1  # картоприемник
circuit_breaker_pin12_state = 1  # цепь автоматов
door_pin6_state = 1  # входная дверь
energy_sensor_pin25_state = 1  # контроль наличия питания R3 (освещения)
window1_pin24_state = 1  # окно 1 (балкон)
window2_pin23_state = 1  # окно 2
window3_pin22_state = 1  # окно 3
switch_main_pin27_state = 1  # выключатель свет в спальне
switch_bl_pin18_state = 1  # выключатель бра левый
switch_br_pin17_state = 1  # выключатель бра правый
flooding_sensor_pin4_state = 1  # датчик затопления ВЩ

close_door_from_inside_counter = 1
open_door_counter = 1


class ProgramKilled(Exception):
    pass


# pin#26 callback (проверка сработки внут защелки (ригеля) на закрытие)
def f_lock_door_from_inside(self):
    if not self.state:
            time.sleep(0.01)
            self.state = GPIO.input(self.pin)
            if not self.state:
                relay2_controller.set_bit(6)  # зажигаем красный светодиод
                logger.info("The door has been locked from inside.")
    time.sleep(0.01)
    if self.state:
        relay2_controller.clear_bit(6)  # тушим красный светодиод


# pin#20 callback (проверка сработки "язычка" на открытие с последующим вызовом функции "закрытия замка")
def f_lock_latch(self):
    time.sleep(0.01)
    self.state = GPIO.input(self.pin)
    if not self.state:
        time.sleep(0.01)
        if not self.state:
            time.sleep(1)
            close_door()


# pin#16 callback (использование ключа)
def f_using_key_pin(pin):
    time.sleep(0.01)
    global using_key_pin16_state
    using_key_pin16_state = GPIO.input(pin)
    if not using_key_pin16_state:
        for i in range(5):
            logger.info("Callback for {pin} pin. The lock is opened with a key. Counter : {counter}"
                        .format(pin=pin, counter=open_door_counter))
            relay2_controller.set_bit(4)
            time.sleep(0.3)
            relay2_controller.clear_bit(4)
            relay2_controller.set_bit(5)
            time.sleep(0.3)
            relay2_controller.clear_bit(5)
            relay2_controller.set_bit(6)
            time.sleep(0.3)
            relay2_controller.clear_bit(6)
            time.sleep(0.5)
        if is_door_locked_from_inside():
            relay2_controller.set_bit(6)


# pin#19 callback (сейф)
def f_safe_pin(pin):
    time.sleep(0.01)
    global safe_pin19_state
    safe_pin19_state = GPIO.input(pin)
    if not safe_pin19_state:
        time.sleep(0.01)
        safe_pin19_state = GPIO.input(pin)
        if not safe_pin19_state:
            logger.info("Callback for {pin} pin. safe. Counter : {counter}"
                        .format(pin=pin, counter=open_door_counter))


# pin#21 callback датчик дыма 1
def f_fire_detector1_pin(pin):
    time.sleep(0.01)
    global fire_detector1_pin21_state
    fire_detector1_pin21_state = GPIO.input(pin)
    if not fire_detector1_pin21_state:
        time.sleep(0.01)
        fire_detector1_pin21_state = GPIO.input(pin)
        if not fire_detector1_pin21_state:
            logger.info("Callback for {pin} pin. fire_detector1. Counter : {counter}"
                        .format(pin=pin, counter=open_door_counter))


# pin#5 callback датчик дыма 2
def f_fire_detector2_pin(pin):
    time.sleep(0.01)
    global fire_detector2_pin5_state
    fire_detector2_pin5_state = GPIO.input(pin)
    if not fire_detector2_pin5_state:
        time.sleep(0.01)
        fire_detector2_pin5_state = GPIO.input(pin)
        if not fire_detector2_pin5_state:
            logger.info("Callback for {pin} pin. fire_detector2. Counter : {counter}"
                        .format(pin=pin, counter=open_door_counter))


# pin#7 callback датчик дыма 3
def f_fire_detector3_pin(pin):
    time.sleep(0.01)
    global fire_detector3_pin7_state
    fire_detector3_pin7_state = GPIO.input(pin)
    if not fire_detector3_pin7_state:
        time.sleep(0.01)
        fire_detector3_pin7_state = GPIO.input(pin)
        if not fire_detector3_pin7_state:
            logger.info("Callback for {pin} pin. card_key. Counter : {counter}"
                        .format(pin=pin, counter=open_door_counter))


# pin#13 callback картоприемник
def f_card_key_pin(pin):
    time.sleep(0.01)
    global card_key_pin13_state
    card_key_pin13_state = GPIO.input(pin)
    if not card_key_pin13_state:
        time.sleep(0.01)
        card_key_pin13_state = GPIO.input(pin)
        if not card_key_pin13_state:
            logger.info("Callback for {pin} pin. fire_detector1. Counter : {counter}"
                        .format(pin=pin, counter=open_door_counter))


# pin#12 callback цепь автоматов
def f_circuit_breaker_pin(pin):
    time.sleep(0.01)
    global circuit_breaker_pin12_state
    circuit_breaker_pin12_state = GPIO.input(pin)
    if not circuit_breaker_pin12_state:
        logger.info("Callback for {pin} pin. circuit_breaker. Counter : {counter}"
                    .format(pin=pin, counter=open_door_counter))


# pin#6 callback входная дверь
def f_door_pin(pin):
    time.sleep(0.01)
    global door_pin6_state
    door_pin6_state = GPIO.input(pin)
    if not door_pin6_state:
        time.sleep(0.01)
        door_pin6_state = GPIO.input(pin)
        if not door_pin6_state:
            logger.info("Callback for {pin} pin. door_pin. Counter : {counter}"
                        .format(pin=pin, counter=open_door_counter))


# pin#25 callback контроль наличия питания R3 (освещения)
def f_energy_sensor_pin(pin):
    time.sleep(0.01)
    global energy_sensor_pin25_state
    energy_sensor_pin25_state = GPIO.input(pin)
    if not energy_sensor_pin25_state:
        time.sleep(0.01)
        energy_sensor_pin25_state = GPIO.input(pin)
        if not energy_sensor_pin25_state:
            logger.info("Callback for {pin} pin. energy_sensor. Counter : {counter}"
                        .format(pin=pin, counter=open_door_counter))


# pin#24 callback окно1 (балкон)
def f_window1_pin(pin):
    time.sleep(0.01)
    global window1_pin24_state
    window1_pin24_state = GPIO.input(pin)
    if not window1_pin24_state:
        time.sleep(0.01)
        window1_pin24_state = GPIO.input(pin)
        if not window1_pin24_state:
            logger.info("Callback for {pin} pin. window1. Counter : {counter}"
                        .format(pin=pin, counter=open_door_counter))
            time.sleep(0.2)


# pin#23 callback окно2
def f_window2_pin(pin):
    time.sleep(0.01)
    global window2_pin23_state
    window2_pin23_state = GPIO.input(pin)
    if not window2_pin23_state:
        time.sleep(0.01)
        window2_pin23_state = GPIO.input(pin)
        if not window2_pin23_state:
            logger.info("Callback for {pin} pin. window2. Counter : {counter}"
                        .format(pin=pin, counter=open_door_counter))


# pin#22 callback окно3
def f_window3_pin(pin):
    time.sleep(0.01)
    global window3_pin22_state
    window3_pin22_state = GPIO.input(pin)
    if not window3_pin22_state:
        time.sleep(0.01)
        window3_pin22_state = GPIO.input(pin)
        if not window3_pin22_state:
            logger.info("Callback for {pin} pin. window3. Counter : {counter}"
                        .format(pin=pin, counter=open_door_counter))


# pin#27 callback выключатель основного света
def f_switch_main_pin(pin):
    time.sleep(0.01)
    global switch_main_pin27_state, lighting_main
    switch_main_pin27_state = GPIO.input(pin)
    if not switch_main_pin27_state:
        time.sleep(0.01)
        switch_main_pin27_state = GPIO.input(pin)
        if not switch_main_pin27_state:
            logger.info("Callback for {pin} pin. lighting_main. "
                        .format(pin=pin))
            if not lighting_main:
                relay2_controller.clear_bit(0)
                lighting_main = True
            else:
                relay2_controller.set_bit(0)
                lighting_main = False
            time.sleep(0.2)


# pin#18 callback выключатель бра левый
def f_switch_bl_pin(pin):
    time.sleep(0.01)
    global switch_bl_pin18_state, lighting_bl
    switch_bl_pin18_state = GPIO.input(pin)
    if not switch_bl_pin18_state:
        time.sleep(0.01)
        switch_bl_pin18_state = GPIO.input(18)
        if not switch_bl_pin18_state:
            logger.info("Callback for {pin} pin. lighting_bl. "
                        .format(pin=pin))
            if not lighting_bl:
                relay1_controller.clear_bit(6)
                lighting_bl = True
            else:
                relay1_controller.set_bit(6)
                lighting_bl = False
            time.sleep(0.2)


# pin#17 callback выключатель бра правый
def f_switch_br_pin(pin):
    time.sleep(0.01)
    global switch_br_pin17_state, lighting_br
    switch_br_pin17_state = GPIO.input(pin)
    if not switch_br_pin17_state:
        time.sleep(0.01)
        switch_br_pin17_state = GPIO.input(pin)
        if not switch_br_pin17_state:
            logger.info("Callback for {pin} pin. lighting_br. "
                        .format(pin=pin))
            if not lighting_br:
                relay1_controller.clear_bit(7)
                lighting_br = True
            else:
                relay1_controller.set_bit(7)
                lighting_br = False
            time.sleep(0.2)


# pin#4 callback датчик затопления ВЩ
def f_flooding_sensor_pin(pin):
    time.sleep(0.01)
    global flooding_sensor_pin4_state
    flooding_sensor_pin4_state = GPIO.input(pin)
    if not flooding_sensor_pin4_state:
        time.sleep(0.01)
        flooding_sensor_pin4_state = GPIO.input(pin)
        if not flooding_sensor_pin4_state:
            logger.info("Callback for {pin} pin. flooding_sensor. Counter : {counter}"
                        .format(pin=pin, counter=open_door_counter))


def is_door_locked_from_inside():
    time.sleep(0.1)
    return not bool(GPIO.input(doors_lock_pin))


# закрытие замка, с предварительной проверкой
def close_door():
    global door_just_closed, can_open_the_door
    if not can_open_the_door:
        logger.info("Door is closed. Permission denied!")  # ????
        return
    relay1_controller.clear_bit(1)
    time.sleep(0.08)
    relay1_controller.set_bit(1)
    can_open_the_door = False
    door_just_closed = True

    logger.info("Client has been entered!")


pin26ctl = None
pin20ctl = None


def init_room():
    logger.info("Init room")
    global pin26ctl
    pin26ctl = PinController(26, f_lock_door_from_inside)   # pin26
    pin20ctl = PinController(20, f_lock_latch)    # pin20 ("язычка")
    GPIO.setup(using_key_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)  # pin16 (открытие замка механическим ключем)
    GPIO.setup(safe_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)  # pin19 (сейф)
    GPIO.setup(fire_detector1_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)  # pin21 датчик дыма 1
    GPIO.setup(fire_detector2_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)  # pin5  датчик дыма 2
    GPIO.setup(fire_detector3_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)  # pin7  датчик дыма 3
    GPIO.setup(card_key_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)  # pin13 картоприемник
    GPIO.setup(circuit_breaker_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)  # pin12 цепь доп контактов автоматов
    GPIO.setup(door_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)  # pin6  входная дверь
    GPIO.setup(energy_sensor_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)  # pin25 контроль наличия питания R3 (освещения)
    GPIO.setup(window1_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)  # pin24 окно 1 (балкон)
    GPIO.setup(window2_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)  # pin23 окно 2
    GPIO.setup(window3_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)  # pin22 окно 3
    GPIO.setup(switch_main_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)  # pin27 выключатель основного света
    GPIO.setup(switch_bl_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)  # pin18 выключатель бра левый
    GPIO.setup(switch_br_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)  # pin17 выключатель бра правый
    GPIO.setup(flooding_sensor_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)  # pin4  датчик затопления ВЩ

    # детекторы сработки с вызовом ф-ии проверки
    GPIO.add_event_detect(using_key_pin, GPIO.BOTH, f_using_key_pin,
                          bouncetime=50)  # pin16 (открытие замка механическим ключем)
    GPIO.add_event_detect(safe_pin, GPIO.FALLING, f_safe_pin, bouncetime=50)  # pin19 (сейф)
    GPIO.add_event_detect(fire_detector1_pin, GPIO.BOTH, f_fire_detector1_pin, bouncetime=50)  # pin21 (датчик дыма 1)
    GPIO.add_event_detect(fire_detector2_pin, GPIO.BOTH, f_fire_detector2_pin, bouncetime=50)  # pin5  (датчик дыма 2)
    GPIO.add_event_detect(fire_detector3_pin, GPIO.BOTH, f_fire_detector3_pin, bouncetime=50)  # pin7  (датчик дыма 3)
    GPIO.add_event_detect(card_key_pin, GPIO.BOTH, f_card_key_pin, bouncetime=50)  # pin13 (картоприемник)
    GPIO.add_event_detect(circuit_breaker_pin, GPIO.BOTH,
                          f_circuit_breaker_pin, bouncetime=50)  # pin12 (цепь допконтактов автоматов)
    GPIO.add_event_detect(door_pin, GPIO.BOTH, f_door_pin, bouncetime=50)  # pin6  (входная дверь)
    GPIO.add_event_detect(energy_sensor_pin, GPIO.BOTH, f_energy_sensor_pin,
                          bouncetime=50)  # pin25 (контроль наличия питания R3 (освещения))
    GPIO.add_event_detect(window1_pin, GPIO.BOTH, f_window1_pin, bouncetime=50)  # pin24 (окно1-балкон)
    GPIO.add_event_detect(window2_pin, GPIO.BOTH, f_window2_pin, bouncetime=50)  # pin23 (окно2)
    GPIO.add_event_detect(window3_pin, GPIO.BOTH, f_window3_pin, bouncetime=50)  # pin22 (окно3)
    GPIO.add_event_detect(switch_main_pin, GPIO.FALLING, f_switch_main_pin,
                          bouncetime=50)  # pin27 (выключатель основного света)
    GPIO.add_event_detect(switch_bl_pin, GPIO.FALLING, f_switch_bl_pin, bouncetime=50)  # pin18 (выключатель бра левый)
    GPIO.add_event_detect(switch_br_pin, GPIO.FALLING, f_switch_br_pin,
                          bouncetime=50)  # pin17 (выключатель бра правый)
    GPIO.add_event_detect(flooding_sensor_pin, GPIO.BOTH, f_flooding_sensor_pin,
                          bouncetime=50)  # pin4  (датчик затопления ВЩ)

    global bus
    # todo: what is the second parameter ?
    #    lock_door_from_inside()
    logger.info("The room has been initiated")


# открытие замка с предварительной проверкой положения pin26(защелка, запрет) и последующим закрытием по таймауту
def permit_open_door():
    global doors_lock_pin, door_just_closed, can_open_the_door
    if is_door_locked_from_inside():
        logger.info("The door has been locked by the guest.")
        
        for i in range(5):
            relay2_controller.set_bit(4)
            relay2_controller.clear_bit(6)
            time.sleep(0.1)
            relay2_controller.set_bit(6)
            relay2_controller.clear_bit(4)
            time.sleep(0.1)
        
            
        if not is_door_locked_from_inside():
            relay2_controller.clear_bit(6)

        
        return
    relay1_controller.clear_bit(0)
    time.sleep(0.08)
    relay1_controller.set_bit(0)
    can_open_the_door = True
    for i in range(50):

        if door_just_closed:
            return

        relay2_controller.set_bit(4)
        time.sleep(0.1)
        relay2_controller.clear_bit(4)
        time.sleep(0.05)

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


def signal_handler(signum, frame):
    raise ProgramKilled


class Pin(threading.Thread):

    def __init__(self, interval):
        global switch_main_pin27_state, switch_bl_pin18_state, switch_br_pin17_state
        threading.Thread.__init__(self)
        self.daemon = False
        self.stopped = threading.Event()
        self.interval = interval

    def stop(self):
        self.stopped.set()
        self.join()

    def run(self):
        global switch_main_pin27_state, switch_bl_pin18_state, switch_br_pin17_state

        while not self.stopped.wait(self.interval.total_seconds()):
            pin26ctl.check_pin()
            f_safe_pin(safe_pin)
            f_fire_detector1_pin(fire_detector1_pin)
            f_fire_detector2_pin(fire_detector2_pin)
            f_fire_detector3_pin(fire_detector3_pin)
            f_card_key_pin(card_key_pin)
            f_circuit_breaker_pin(circuit_breaker_pin)
            f_door_pin(door_pin)
            f_energy_sensor_pin(energy_sensor_pin)
            f_window1_pin(window1_pin)
            f_window2_pin(window2_pin)
            f_window3_pin(window3_pin)
            f_switch_main_pin(switch_main_pin)
            f_switch_bl_pin(switch_bl_pin)
            f_switch_br_pin(switch_br_pin)
            f_flooding_sensor_pin(flooding_sensor_pin)

            print("pin_state           :", lighting_bl,
                  lighting_br,
                  lighting_main,
                  doors_lock_pin26_state,
                  safe_pin19_state,
                  fire_detector1_pin21_state,
                  fire_detector2_pin5_state,
                  fire_detector3_pin7_state,
                  card_key_pin13_state,
                  circuit_breaker_pin12_state,
                  door_pin6_state,
                  energy_sensor_pin25_state,
                  window1_pin24_state,
                  window2_pin23_state,
                  window3_pin22_state,
                  switch_main_pin27_state,
                  switch_bl_pin18_state,
                  switch_br_pin17_state,
                  flooding_sensor_pin4_state)

            print("GPIO IN - 27, 18, 17: ", GPIO.input(27), GPIO.input(18), GPIO.input(17))


class Job(threading.Thread):
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
    job = Job(interval=timedelta(seconds=system_config.new_key_check_interval), execute=get_active_cards)
    job.start()
    pin = Pin(interval=timedelta(seconds=10))
    pin.start()
    init_room()

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
                for i in range(5):
                    relay2_controller.set_bit(6)
                    time.sleep(0.1)
                    relay2_controller.clear_bit(6)
                    time.sleep(0.05)
        except ProgramKilled:
            logger.info("Program killed: running cleanup code")
            job.stop()
            break
