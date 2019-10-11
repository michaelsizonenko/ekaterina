import threading
import time
import signal
from datetime import datetime, timedelta
import pymssql


WAIT_SECONDS = 300
ROOM_NUMBER = 888
ACTIVE_CARDS = []
MSSQL_SETTINGS = {
    'server': '192.168.9.241',
    'user': 'user',
    'password': '123',
    'database': 'kluch'
}


class ProgramKilled(Exception):
    pass


def get_active_cards():
    conn = pymssql.connect(**MSSQL_SETTINGS)
    cursor = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    sql = f"SELECT * FROM table_kluch WHERE dstart <= '{now}' AND dend >= '{now}' AND (tip = 1 OR tip = 0) AND num = {ROOM_NUMBER}"
    cursor.execute(sql)
    result = cursor.fetchall()
    print(result)


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
            time.sleep(1)
            print("main task")
        except ProgramKilled:
            print("Program killed: running cleanup code")
            job.stop()
            break
