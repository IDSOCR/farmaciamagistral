import sqlite3

DB_NAME = "base.db"

with sqlite3.connect(DB_NAME) as conn:
    cursor = conn.cursor()

    # Verificamos si las columnas ya existen, si no, las agregamos
    try:
        cursor.execute("ALTER TABLE ventas ADD COLUMN año INTEGER")
        cursor.execute("ALTER TABLE ventas ADD COLUMN mes INTEGER")
        cursor.execute("ALTER TABLE ventas ADD COLUMN día INTEGER")
        print("Columnas añadidas correctamente.")
    except sqlite3.OperationalError as e:
        print("Ya se habían agregado las columnas o hubo un error:", e)
