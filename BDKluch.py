import sqlite3

conn = sqlite3.connect("BDKluch.db") # или :memory: чтобы сохранить в RAM
cursor = conn.cursor()

#(num, kl, dstart, dend, flag, tip, tekdat, id, rpi)


cursor.execute("""INSERT INTO Kluch
                  VALUES (1, 2, 3,
                   4, 5, 6, 7, 8, 9)
                   """)
conn.commit()

sql = "SELECT * FROM BDKluch WHERE num=?"
cursor.execute(sql, [("1")])
print(cursor.fetchall()) 

print("Here's a listing of all the records in the table:")
for row in cursor.execute("SELECT rowid, * FROM albums ORDER BY artist"):
    print(row)

print("Results from a LIKE query:")
sql = "SELECT * FROM albums WHERE title LIKE 'The%'"
cursor.execute(sql)

print(cursor.fetchall())