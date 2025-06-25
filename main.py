from flask import Flask, render_template, request, session, redirect, url_for
from flask_socketio import join_room, leave_room, emit, SocketIO
import random
from string import ascii_uppercase
from datetime import datetime
import sys

#Generar color aleatorio
def colorAleatorio():
    letras = '0123456789ABCDEF'
    color = '#'
    for _ in range(6):
        color += random.choice(letras)
    return color



# Creamos el Web Server con Flask
app = Flask(__name__)
app.config['SECRET_KEY'] = 'd2025fml'
socketio = SocketIO(app)

salas = {}


# Funcion para crear codigos de sala
def generar_codigo_unico(caracteres):
    while True:
        codigo = ""
        for _ in range(caracteres):
            codigo += random.choice(ascii_uppercase)

        if codigo not in salas:
            break
    return codigo


# Creamos las rutas
# Homepage
@app.route("/", methods=["POST", "GET"])
def inicio():
    session.clear()
    if request.method == "POST":
        nombre = request.form.get("nombre")
        codigo_sala = request.form.get("codigo")
        unirse = request.form.get("unirse", False)  # Por defecto es False
        crear = request.form.get("crear", False)

        if not nombre:
            return render_template("inicio.html", error="Ingrese un nombre.", codigo=codigo_sala, nombre=nombre)

        if unirse and not codigo_sala:
            return render_template("inicio.html", error="Ingrese un codigo de sala.", codigo=codigo_sala, nombre=nombre)

        sala = codigo_sala
        if crear:
            sala = generar_codigo_unico(4)
            salas[sala] = {"miembros": 0, "mensajes": []}
        elif codigo_sala not in salas:
            return render_template("inicio.html", error="La sala no existe.", codigo=codigo_sala, nombre=nombre)
        session["color"] = colorAleatorio()
        session["sala"] = sala  # session es de Flask
        session["nombre"] = nombre
        return redirect(url_for("sala"))

    return render_template("inicio.html")


# Salas de chat
@app.route("/sala")
def sala():
    sala = session.get("sala")
    if sala is None or session.get("nombre") is None or sala not in salas:
        return redirect(url_for("inicio"))
    return render_template("sala.html", codigo=sala, mensajes=salas[sala]["mensajes"])

# Unirse a la sala (conectarse al socket)
@socketio.on("connect")
def conectarse(auth):
    sala = session.get("sala")
    nombre = session.get("nombre")
    if not sala or not nombre:
        return
    if sala not in salas:
        leave_room(sala)  # método de socketio
        return

    join_room(sala)  # método de socketio
    emit("mensaje", {"nombre": nombre, "mensaje_unirse": "se unió a la sala", "timestamp": datetime.now().isoformat()}, to=sala)  # método de socketio
    salas[sala]["miembros"] += 1
    print(f"{nombre} se unió a la sala {sala}")

# Abandonar la sala (deconectarse del socket)
@socketio.on("disconnect")
def desconectarse():
    sala = session.get("sala")
    nombre = session.get("nombre")
    leave_room(sala)

    if sala in salas:
        salas[sala]["miembros"] -= 1
        if salas[sala]["miembros"] <= 0:
            del salas[sala]

    emit("mensaje", {"nombre": nombre, "mensaje_abandono": "abandonó la sala", "timestamp": datetime.now().isoformat()}, to=sala)
    print(f"{nombre} abandonó la sala {sala}")

# Manejar los mensajes enviados y transmitirlos a todos los que esten en la sala correspondiente
@socketio.on("mensaje")
def mensaje(data):
    sala = session.get("sala")
    if sala not in salas:
        return

    contenido = {
        "nombre": session.get("nombre"),
        "mensaje": data["data"],
        "color": session.get("color"),
        "timestamp": datetime.now().isoformat()
    }
    emit("mensaje", contenido, to=sala)
    salas[sala]["mensajes"].append(contenido)
    print(f"{session.get('nombre')} mandó un mensaje: {data['data']}")


if __name__ == "__main__":
    # Obtener el puerto desde argumentos de línea de comandos, por defecto 5000
    puerto = 5000
    if len(sys.argv) > 1:
        try:
            puerto = int(sys.argv[1])
        except ValueError:
            print("Error: El puerto debe ser un número entero")
            print("Uso: python main.py [puerto]")
            sys.exit(1)
    
    print(f"Servidor iniciando en el puerto {puerto}")
    socketio.run(app, host="0.0.0.0", port=puerto, debug=False, allow_unsafe_werkzeug=True)

