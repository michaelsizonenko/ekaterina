import threading
import time
import signal
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
doors_lock_pin = 26

active_cards = []


class ProgramKilled(Exception):
    pass


def lock_door(pin):
    state = GPIO.input(pin)
    if state:
        print("door locked!")
    else:
        print("door unlocked!")


def init_room():
    global doors_lock_pin
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(doors_lock_pin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
    GPIO.add_event_detect(doors_lock_pin, GPIO.BOTH, lock_door)


def open_door():
    global doors_lock_pin
    is_door_locked = GPIO.input(doors_lock_pin)
    if is_door_locked:
        print("The door has been locked by the guest.")
        return
    raise NotImplementedError


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
