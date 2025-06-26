import datetime
import sqlite3

def connection_db():
    conn = sqlite3.connect('tennis.sqlite3')
    conn.row_factory = sqlite3.Row
    return conn


def create_db():
    conn = connection_db()
    cur = conn.cursor()
    cur.execute('CREATE TABLE IF NOT EXISTS bookKORT(id integer PRIMARY KEY AUTOINCREMENT, \
                                    user VARCHAR(30), \
                                    time_create DATETIME,\
                                    time_start DATETIME,\
                                    time_finish DATETIME)')
    conn.commit()
    cur.close()
    conn.close()


def add_note(user, time_start, time_finish):
    conn = connection_db()
    cur = conn.cursor()
    sql = f'INSERT INTO bookKORT VALUES (NULL, ?, datetime("now", "localtime"), ?, ?)'
    try:
        cur.execute(sql, (user, time_start, time_finish))
        conn.commit()
        cur.close()
        conn.close()
    except sqlite3.Error as e:
        print("Ошибка добавления данных" + str(e))


if __name__ == "__main__":
    create_db()

