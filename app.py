from flask import Flask, render_template, request, redirect, send_file
import sqlite3
import pandas as pd
from io import BytesIO
from datetime import datetime

app = Flask(__name__)
DB_NAME = 'base.db'

# Crear la tabla si no existe
def init_db():
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()

        # Tabla principal con columnas adicionales de año, mes, día
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ventas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                farmacia TEXT,
                orden TEXT,
                descripcion TEXT,
                monto_farmacia REAL,
                venta_final REAL,
                monto_20 REAL,
                iva_2 REAL,
                comision_50 REAL,
                estado TEXT,
                fecha TEXT,
                año INTEGER,
                mes INTEGER,
                día INTEGER
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS farmacias (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT UNIQUE
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS estados (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT UNIQUE
            )
        ''')

        cursor.executemany("INSERT OR IGNORE INTO farmacias(nombre) VALUES (?)", [
            ('Ejemplo 1',), ('Ejemplo 2',), ('Ejemplo 3',)
        ])

        cursor.executemany("INSERT OR IGNORE INTO estados(nombre) VALUES (?)", [
            ('Pendiente',), ('Pagado',), ('Anulado',)
        ])

        conn.commit()


@app.route('/')
def index():
    anio = request.args.get("anio")
    mes = request.args.get("mes")
    estado_filtro = request.args.get("estado")
    farmacia_filtro = request.args.get("farmacia") #agregado

    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()

        query = "SELECT * FROM ventas"
        filtros = []
        valores = []

        if anio:
            filtros.append("año = ?")
            valores.append(anio)
        if mes:
            filtros.append("mes = ?")
            valores.append(mes)
        if estado_filtro:
            filtros.append("estado = ?")
            valores.append(estado_filtro)
        #agregado
        if farmacia_filtro:
            filtros.append("farmacia = ?")
            valores.append(farmacia_filtro)    

        if filtros:
            query += " WHERE " + " AND ".join(filtros)

        query += " ORDER BY fecha DESC"
        cursor.execute(query, valores)
        ventas = cursor.fetchall()

        cursor.execute("SELECT nombre FROM farmacias")
        farmacias = [f[0] for f in cursor.fetchall()]

        cursor.execute("SELECT nombre FROM estados")
        estados = [e[0] for e in cursor.fetchall()]

        cursor.execute("SELECT DISTINCT año FROM ventas ORDER BY año DESC")
        anios_disponibles = [str(a[0]) for a in cursor.fetchall()]

    return render_template('index.html',
        ventas=ventas,
        farmacias=farmacias,
        estados=estados,
        anios_disponibles=anios_disponibles,
        anio=anio,
        mes=mes,
        estado_filtro=estado_filtro, #agregado desde la ,
        farmacia_filtro=farmacia_filtro
    )




@app.route('/registrar', methods=['POST'])
def registrar():
    farmacia = request.form['farmacia']
    orden = request.form['orden']
    descripcion = request.form['descripcion']
    estado = request.form['estado']
    monto_farmacia = float(request.form['monto_farmacia'])
    venta_final = float(request.form['venta_final'])

    monto_20 = monto_farmacia * 0.20 + monto_farmacia
    iva_2 = monto_farmacia * 0.02
    comision_50 = ((venta_final - monto_farmacia) / 2) - iva_2

    ahora = datetime.now()
    fecha = ahora.strftime("%Y-%m-%d %H:%M:%S")
    anio = ahora.year
    mes = ahora.month
    dia = ahora.day

    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO ventas (
                farmacia, orden, descripcion, monto_farmacia, venta_final,
                monto_20, iva_2, comision_50, estado, fecha, año, mes, día
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (farmacia, orden, descripcion, monto_farmacia, venta_final,
              monto_20, iva_2, comision_50, estado, fecha, anio, mes, dia))
        conn.commit()

    return redirect('/')


@app.route('/descargar')
def descargar():
    with sqlite3.connect(DB_NAME) as conn:
        df = pd.read_sql_query("SELECT * FROM ventas", conn)

    output = BytesIO()
    df.to_excel(output, index=False)
    output.seek(0)

    return send_file(output, download_name='ventas_farmacia.xlsx', as_attachment=True)


@app.route('/admin', methods=['GET', 'POST'])
def admin():
    mensaje = ""
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()

        if request.method == 'POST':
            tipo = request.form.get('tipo')
            valor = request.form.get('valor')

            if tipo == 'farmacia':
                cursor.execute("INSERT OR IGNORE INTO farmacias(nombre) VALUES (?)", (valor,))
                mensaje = f"Farmacia '{valor}' agregada."
            elif tipo == 'estado':
                cursor.execute("INSERT OR IGNORE INTO estados(nombre) VALUES (?)", (valor,))
                mensaje = f"Estado '{valor}' agregado."
            conn.commit()

        cursor.execute("SELECT id, nombre FROM farmacias")
        farmacias = cursor.fetchall()

        cursor.execute("SELECT id, nombre FROM estados")
        estados = cursor.fetchall()

    return render_template('admin.html', farmacias=farmacias, estados=estados, mensaje=mensaje)


@app.route('/editar_auxiliar', methods=['POST'])
def editar_auxiliar():
    tipo = request.form.get('tipo')
    id_ = request.form.get('id')
    nuevo = request.form.get('nuevo')

    tabla = 'farmacias' if tipo == 'farmacia' else 'estados'

    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute(f"UPDATE {tabla} SET nombre = ? WHERE id = ?", (nuevo, id_))
        conn.commit()

    return redirect('/admin')


@app.route('/editar/<int:id>', methods=['GET', 'POST'])
def editar(id):
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()

        if request.method == 'POST':
            farmacia = request.form['farmacia']
            orden = request.form['orden']
            descripcion = request.form['descripcion']
            estado = request.form['estado']
            monto_farmacia = float(request.form['monto_farmacia'])
            venta_final = float(request.form['venta_final'])

            monto_20 = monto_farmacia * 0.20
            iva_2 = monto_farmacia * 0.02
            comision_50 = ((venta_final - monto_farmacia) / 2) - iva_2

            cursor.execute('''
                UPDATE ventas SET
                    farmacia = ?, orden = ?, descripcion = ?, monto_farmacia = ?, venta_final = ?,
                    monto_20 = ?, iva_2 = ?, comision_50 = ?, estado = ?
                WHERE id = ?
            ''', (farmacia, orden, descripcion, monto_farmacia, venta_final,
                  monto_20, iva_2, comision_50, estado, id))
            conn.commit()
            return redirect('/')

        # Cargar datos actuales
        cursor.execute("SELECT * FROM ventas WHERE id = ?", (id,))
        venta = cursor.fetchone()

        cursor.execute("SELECT nombre FROM farmacias")
        farmacias = [f[0] for f in cursor.fetchall()]

        cursor.execute("SELECT nombre FROM estados")
        estados = [e[0] for e in cursor.fetchall()]

    return render_template('editar.html', venta=venta, farmacias=farmacias, estados=estados)

@app.route('/eliminar_auxiliar', methods=['POST'])
def eliminar_auxiliar():
    tipo = request.form.get('tipo')
    id_ = request.form.get('id')

    tabla = 'farmacias' if tipo == 'farmacia' else 'estados'

    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute(f"DELETE FROM {tabla} WHERE id = ?", (id_,))
        conn.commit()

    return redirect('/admin')



if __name__ == '__main__':
    init_db()
    app.run(debug=True)






