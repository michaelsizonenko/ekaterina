import threading
import time
import signal
import smbus
from datetime import datetime, timedelta
import pymssql
import serial
import RPi.GPIO as GPIO
from relaycontroller import RelayController
from config import Config


door_just_closed = False
can_open_the_door = False
db_connection = None
bus = smbus.SMBus(1)
doors_lock_pin = 26
lock_tongue_pin = 20
open_lock_cmd = 1
close_lock_cmd = 2
relay1_controller = RelayController(0x38)

active_cards = []

#apin20 = 1
#apin26 = 1
pin20_state = 1
pin26_state = 1


k = 1
o = 1

config = Config()


class ProgramKilled(Exception):
    pass


# pin#26 callback
def lock_door_from_inside(pin):  # проверка сработки "язычка" на открытие
    time.sleep(0.01)
#    global apin26
    global k
    global pin26_state
    pin26_state = GPIO.input(pin)
    if not pin26_state:
        time.sleep(0.01)
        if not pin26_state:
            #            pin26_state = GPIO.input(pin)
            #            apin26 = pin26_state
            print("lock_door_from_inside")
            print("k=", k)
            k = k + 1


# pin#20 callback
def open_door_callback(pin):  # проверка сработки внут защелки (ригеля) на закрытие
    time.sleep(0.01)
#    global apin20
    global o
    global pin20_state
    pin20_state = GPIO.input(pin)
    if not pin20_state:
        time.sleep(0.01)
        if not pin20_state:
            #            pin20_state = GPIO.input(pin)
            #            apin20 = pin20_state
            print("{pin} callback".format(pin=pin))
            print("O=", o)
            o = o + 1
            #            if is_door_locked_from_inside():                                     # ???????
            #                return
            close_door()


def is_door_locked_from_inside():
    time.sleep(0.1)
    return not bool(GPIO.input(doors_lock_pin))


def close_door():
    global door_just_closed, can_open_the_door
    if not can_open_the_door:
        print("Door is closed. Permission denied!")
        return
    relay1_controller.clear_bit(1)
    time.sleep(0.2)
    relay1_controller.set_bit(1)
    can_open_the_door = False
    door_just_closed = True
    print("Client has been entered!")


def init_room():
    print("Init room")
    global doors_lock_pin, lock_tongue_pin
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(doors_lock_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.setup(lock_tongue_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.add_event_detect(doors_lock_pin, GPIO.FALLING, lock_door_from_inside)  # добавляем  детектор сработки "язычка" на открытие с вызовом ф-ии "проверка сработки "язычка" на открытие"
    GPIO.add_event_detect(lock_tongue_pin, GPIO.FALLING, open_door_callback)  # добавляем детектор сработки внут защелки (ригеля) на закрытие с вызовом ф-ии "проверка сработки внут защелки (ригеля) на закрытие"
    global bus
    # todo: what is the second parameter ?
#    lock_door_from_inside()
    print("The room has been initiated")


def permit_open_door():
    global doors_lock_pin, door_just_closed, can_open_the_door
    if is_door_locked_from_inside():
        print("The door has been locked by the guest.")
        return
    relay1_controller.clear_bit(0)
    time.sleep(0.2)
    relay1_controller.set_bit(0)
    can_open_the_door = True
    #    GPIO.add_event_callback(lock_tongue_pin, GPIO.FALLING, open_door_callback)

    for i in range(5):

        if door_just_closed:
            return
        time.sleep(1)
    close_door()
    #    GPIO.remove_event_detect(lock_tongue_pin)
    print("Nobody entered")


def handle_table_row(row_):
    return row_[config.rfig_key_table_index].replace(" ", "").encode("UTF-8")


def get_db_connection():
    global db_connection
    if db_connection is None:
        db_connection = pymssql.connect(**config.db_config.__dict__)
    return db_connection


def get_active_cards():
    cursor = get_db_connection().cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    sql = "SELECT * FROM table_kluch WHERE dstart <= '{now}' AND dend >= '{now}' AND (tip = 1 OR tip = 0) AND num = {room_number}".format(now=now, room_number=config.room_number)
    cursor.execute(sql)
    key_list = cursor.fetchall()
    global active_cards
    active_cards = [handle_table_row(row) for row in key_list]


def wait_rfid():
    rfid_port = serial.Serial('/dev/serial0')
    key_ = rfid_port.read(config.rfid_key_length)[1:11]
    print("key catched {key} {datetime}".format(key=key_, datetime=datetime.utcnow()))
    return key_

def wait_rfid1():
    rfid_port = serial.Serial('/dev/ttyUSB0')
    key_ = rfid_port.read(config.rfid_key_length)[1:11]
    print("key catched {key} {datetime}".format(key=key_, datetime=datetime.utcnow()))
    return key_


def signal_handler(signum, frame):
    raise ProgramKilled


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
    job = Job(interval=timedelta(seconds=config.new_key_check_interval), execute=get_active_cards)
    job.start()

    init_room()
    while True:
        try:
            print("Waiting for the key")
            door_just_closed = False
            entered_key = wait_rfid()
            if entered_key in active_cards:
                print("Correct key! Please enter!")
                permit_open_door()
            else:
                print("Unknown key!")
        except ProgramKilled:
            print("Program killed: running cleanup code")
            job.stop()
            break
