from flask import Flask, render_template, request, session, redirect, url_for
from flask_socketio import join_room, leave_room, send, SocketIO
import random
from string import ascii_uppercase

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
    send({"nombre": nombre, "mensaje": "se unió a la sala"}, to=sala)  # método de socketio
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

    send({"nombre": nombre, "mensaje": "abandonó la sala"}, to=sala)
    print(f"{nombre} abandonó la sala {sala}")

# Manejar los mensajes enviados y transmitirlos a todos los que esten en la sala correspondiente
@socketio.on("mensaje")
def mensaje(data):
    sala = session.get("sala")
    if sala not in salas:
        return

    contenido = {
        "nombre": session.get("nombre"),
        "mensaje": data["data"]
    }
    send(contenido, to=sala)
    salas[sala]["mensajes"].append(contenido)
    print(f"{session.get("nombre")} mandó un mensaje: {data['data']}")

if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", debug=True, allow_unsafe_werkzeug=True)