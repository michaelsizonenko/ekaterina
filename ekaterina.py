import time, threading
import pymssql
from datetime import datetime, timedelta

WAIT_SECONDS = 60
ROOM_NUMBER = 888
ACTIVE_CARDS = []
MSSQL_SETTINGS = {
    'server': '192.168.9.241',
    'user': 'user',
    'password': '123',
    'database': 'kluch'
}


def get_active_cards():
    conn = pymssql.connect(**MSSQL_SETTINGS)
    cursor = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    sql = f"SELECT * FROM table_kluch WHERE dstart <= '{now}' AND dend >= '{now}' AND (tip = 1 OR tip = 0) AND num = {ROOM_NUMBER}"
    cursor.execute(sql)
    result = cursor.fetchall()
    print(result)
    threading.Timer(WAIT_SECONDS, get_active_cards).start()


if __name__ == "main":
    get_active_cards()

# while True:
#       print("main cycle {}".format(time.ctime()))
#       time.sleep(2)
