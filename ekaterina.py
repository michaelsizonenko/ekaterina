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
db_connection = None
bus = smbus.SMBus(1)
doors_lock_pin = 26
lock_tongue_pin = 20
open_lock_cmd = 0x01
close_lock_cmd = 0x02
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


def lock_door(pin):
    state = GPIO.input(pin)
    if state:
        print("door locked!")
    else:
        print("door unlocked!")


def try_open_door(pin):
    print(bus.read_byte(relay_addr))
    bus.write_byte_data(relay_addr, 0x09, bus.read_byte(relay_addr) + open_lock_cmd - close_lock_cmd)
    time.sleep(1)
    print(bus.read_byte(relay_addr))
    bus.write_byte_data(relay_addr, 0x09, bus.read_byte(relay_addr) + close_lock_cmd)


def init_room():
    global doors_lock_pin
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(doors_lock_pin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
    GPIO.setup(lock_tongue_pin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
    GPIO.add_event_detect(doors_lock_pin, GPIO.BOTH, lock_door)
    GPIO.add_event_detect(lock_tongue_pin, GPIO.RISING, try_open_door)
    global bus
    bus.write_byte_data(relay_addr, 0x09, 0xff)


def open_door():
    global doors_lock_pin
    is_door_locked = GPIO.input(doors_lock_pin)
    if is_door_locked:
        print("The door has been locked by the guest.")
        return
    print(bus.read_byte(relay_addr))
    bus.write_byte_data(relay_addr, 0x09, bus.read_byte(relay_addr) - open_lock_cmd)
    time.sleep(10)
    print(bus.read_byte(relay_addr))
    bus.write_byte_data(relay_addr, 0x09, bus.read_byte(relay_addr) + open_lock_cmd - close_lock_cmd)
    time.sleep(1)
    print(bus.read_byte(relay_addr))
    bus.write_byte_data(relay_addr, 0x09, bus.read_byte(relay_addr) + close_lock_cmd)
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
    sql = f"SELECT * FROM table_kluch WHERE dstart <= '{now}' AND dend >= '{now}' AND (tip = 1 OR tip = 0) AND num = {ROOM_NUMBER}"
    cursor.execute(sql)
    key_list = cursor.fetchall()
    global active_cards
    active_cards = [handle_table_row(row) for row in key_list]


def wait_rfid():
    rfid_port = serial.Serial('/dev/serial0')
    key_ = rfid_port.read(KEY_LENGTH)[1:11]
    print(f"key catched {key_}")
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
                open_door()
            else:
                print("Unknown key!")
            time.sleep(5)
        except ProgramKilled:
            print("Program killed: running cleanup code")
            job.stop()
            break
