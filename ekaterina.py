import threading
import time
import signal
from datetime import datetime, timedelta
import pymssql
import serial

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

active_cards = []


class ProgramKilled(Exception):
    pass


def handle_table_row(row_):
    return row_[KEY].replace(" ", "").encode("UTF-8")


def get_active_cards():
    conn = pymssql.connect(server='192.168.9.241', user='user', password='123', database='kluch')
    cursor = conn.cursor()
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

    while True:
        try:
            print("main task")
            entered_key = wait_rfid()
            if entered_key in active_cards:
                print("Correct key! Please enter!")
            else:
                print("Unknown key!")
            time.sleep(5)
        except ProgramKilled:
            print("Program killed: running cleanup code")
            job.stop()
            break
