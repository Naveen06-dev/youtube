import sqlite3

conn = sqlite3.connect(r'd:\Projects\utube_final\utube_final\backend\app\database\users.db')
cursor = conn.cursor()
cursor.execute('SELECT id, name, email FROM users')
rows = cursor.fetchall()
conn.close()

with open('db_output.txt', 'w') as f:
    f.write("ID | Name | Email\n")
    f.write("-" * 50 + "\n")
    for row in rows:
        f.write(f"{row[0]:<3} | {row[1]:<20} | {row[2]}\n")
