import threading
import time
import signal
import smbus
from datetime import datetime, timedelta
import pymssql
import serial
import RPi.GPIO as GPIO

WAIT_SECONDS = 300
ROOM_NUMBER = 888
KEY = 1
KEY_LENGTH = 14
MSSQL_SETTINGS = {
    'server': '192.168.9.241',
    'user': 'user',
    'password': '123',
    'database': 'kluch'
}
door_just_closed = False
db_connection = None
bus = smbus.SMBus(1)
doors_lock_pin = 26
lock_tongue_pin = 20
open_lock_cmd = 1
close_lock_cmd = 2
relay_addr = 0x38

active_cards = []


class ProgramKilled(Exception):
    pass


def bin_to_int(bin_):
    return int(bin_, 2)


def hex_to_dec(hex_):
    return int(hex_, 16)


def hex_to_bin(hex_):
    return bin(hex_to_dec(hex_))


def lock_door_from_inside(pin):
    state = GPIO.input(pin)
    if state:
        print("The door is locked from the inside!")
    else:
        print("The door is unlocked!")


def is_door_locked_from_inside():
    return bool(GPIO.input(doors_lock_pin))


def change_byte(position, state):
    l_ = list(str(bin(bus.read_byte(0x38))))
    l_[-position] = str(int(state))
    new_relay_state = int("".join(l_), 2)
    bus.write_byte_data(0x38, 0x09, new_relay_state)


def set_byte_to_zero(position):
    change_byte(position, True)


def set_byte_to_one(position):
    change_byte(position, False)


def close_door():
    global door_just_closed
    print(bus.read_byte(relay_addr))
    set_byte_to_one(2)
    time.sleep(0.1)
    print(bus.read_byte(relay_addr))
    set_byte_to_zero(1)
    time.sleep(1)
    print(bus.read_byte(relay_addr))
    set_byte_to_zero(2)
    door_just_closed = True
    print("Client has been entered!")


def open_door_callback(pin):
    if is_door_locked_from_inside():
        return
    close_door()


def init_room():
    global doors_lock_pin
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(doors_lock_pin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
    GPIO.setup(lock_tongue_pin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
    GPIO.add_event_detect(doors_lock_pin, GPIO.BOTH, lock_door_from_inside)
    GPIO.add_event_detect(lock_tongue_pin, GPIO.RISING, open_door_callback)
    global bus
    bus.write_byte_data(relay_addr, 0x09, 0xff)


def permit_open_door():
    global doors_lock_pin, door_just_closed
    if is_door_locked_from_inside():
        print("The door has been locked by the guest.")
        return
    print(bus.read_byte(relay_addr))
    set_byte_to_one(1)
    time.sleep(10)
    if door_just_closed:
        return
    close_door()
    print("Nobody entered")


def handle_table_row(row_):
    return row_[KEY].replace(" ", "").encode("UTF-8")


def get_db_connection():
    global db_connection
    if db_connection is None:
        db_connection = pymssql.connect(**MSSQL_SETTINGS)
    return db_connection


def get_active_cards():
    cursor = get_db_connection().cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    sql = "SELECT * FROM table_kluch WHERE dstart <= '{now}' AND dend >= '{now}' AND (tip = 1 OR tip = 0) AND num = {room_number}".format(now=now, room_number=ROOM_NUMBER)
    cursor.execute(sql)
    key_list = cursor.fetchall()
    global active_cards
    active_cards = [handle_table_row(row) for row in key_list]


def wait_rfid():
    rfid_port = serial.Serial('/dev/serial0')
    key_ = rfid_port.read(KEY_LENGTH)[1:11]
    print("key catched {key}".format(key=key_))
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
    job = Job(interval=timedelta(seconds=WAIT_SECONDS), execute=get_active_cards)
    job.start()

    init_room()
    while True:
        try:
            print("main task")
            entered_key = wait_rfid()
            if entered_key in active_cards:
                print("Correct key! Please enter!")
                permit_open_door()
            else:
                print("Unknown key!")
            time.sleep(5)
        except ProgramKilled:
            print("Program killed: running cleanup code")
            job.stop()
            break
