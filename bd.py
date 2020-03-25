from datetime import datetime
import pymssql


# cursor.execute("SELECT COUNT(*) FROM table_kluch")
# print("row count in table : %s \n" % cursor.fetchone()[0])

# column names: num,kl,dstart,dend,flag,tip,tekdat,id,rpi
# rpi - флаг прочтения малинкой. после прочтения помечать rpi(raspberry pi) в положение истина
room_number = 888
b'000037623E'
KEY = 1


def handle_table_row(row_):
    return row_[KEY].replace(" ", "").encode("UTF-8")


def get_active_cards():
    conn = pymssql.connect(server='192.168.9.241', user='user', password='123', database='kluch')
    cursor = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    sql = "SELECT * FROM table_kluch WHERE dstart <= '{now}' AND dend >= '{now}' AND (tip = 1 OR tip = 0) AND num = {" \
          "room_number}".format(now=now, room_number=system_config.room_number)
    cursor.execute(sql)
    key_list = cursor.fetchall()
    return [handle_table_row(row) for row in key_list]


active_cards = get_active_cards()
print(" active cards count {len(active_cards)}")
for card in active_cards:
    print(card)


# todo: select only active keys
