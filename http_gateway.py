import os
import json
import socket
from functools import wraps

from flask import (
    Flask, render_template, request, redirect,
    url_for, session, flash, abort
)
from dotenv import load_dotenv

# --- Carga .env ---
load_dotenv()

# --- Configuración ---
SECRET_KEY = os.getenv("SECRET_KEY", "dev")
SOCKET_HOST = os.getenv("SOCKET_HOST", "127.0.0.1")
SOCKET_PORT = int(os.getenv("SOCKET_PORT", "6000"))
SOCKET_ADDR = (SOCKET_HOST, SOCKET_PORT)

FLASK_HOST = os.getenv("FLASK_HOST", "127.0.0.1")
FLASK_PORT = int(os.getenv("FLASK_PORT", "5000"))
FLASK_DEBUG = os.getenv("FLASK_DEBUG", "true").lower() == "true"

# --- App Flask ---
app = Flask(__name__, template_folder="templates", static_folder="static")
app.secret_key = SECRET_KEY

# --- Utilidades ---
def socket_rpc(op: str, data: dict, timeout: float = 5.0) -> dict:
    payload = json.dumps({"op": op, "data": data}) + "\n"
    try:
        with socket.create_connection(SOCKET_ADDR, timeout=timeout) as s:
            s.sendall(payload.encode("utf-8"))
            resp = b""
            while not resp.endswith(b"\n"):
                chunk = s.recv(4096)
                if not chunk:
                    break
                resp += chunk
    except (ConnectionRefusedError, TimeoutError, OSError) as e:
        return {"ok": False, "error": f"No se pudo contactar al servidor de sockets: {e}"}
    try:
        return json.loads(resp.decode("utf-8"))
    except Exception:
        return {"ok": False, "error": "Respuesta inválida del servidor de sockets"}

def login_required(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        if not session.get("user"):
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapper

# --- Rutas ---
@app.get("/")
@login_required
def home():
    return redirect(url_for("inicio"))

@app.get("/inicio")
@login_required
def inicio():
    u = session.get("user")
    p = session.get("_p", "")
    r = socket_rpc("GET_TAREAS_HTML", {"username": u, "password": p})
    if r.get("ok"):
        return render_template("inicio.html", html=r.get("html", ""))
    if r.get("error") == "401 Unauthorized":
        flash("Sesión inválida. Volvé a iniciar sesión.", "danger")
        return redirect(url_for("login"))
    abort(500, description=r.get("error") or "Error al obtener inicio")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        u = (request.form.get("username") or "").strip()
        p = request.form.get("password") or ""
        if not u or not p:
            flash("Usuario y contraseña son requeridos.", "danger")
            return render_template("register.html")

        r = socket_rpc("REGISTRO", {"username": u, "password": p})
        if r.get("ok"):
            flash("Usuario creado, ahora podés iniciar sesión.", "success")
            return redirect(url_for("login"))
        flash(r.get("info") or r.get("error") or "Error al registrar.", "danger")
    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        u = (request.form.get("username") or "").strip()
        p = request.form.get("password") or ""
        if not u or not p:
            flash("Usuario y contraseña son requeridos.", "danger")
            return render_template("login.html")

        r = socket_rpc("LOGIN", {"username": u, "password": p})
        if r.get("ok"):
            session.clear()
            session["user"] = u
            session["_p"] = p
            return redirect(url_for("inicio"))
        flash("Credenciales inválidas.", "danger")
    return render_template("login.html")

@app.get("/logout")
@login_required
def logout():
    session.clear()
    return redirect(url_for("login"))

# --- Vista de tareas (sum, upper, lower) ---
@app.route("/tareas", methods=["GET", "POST"])
@login_required
def tareas():
    result = None
    error = None

    if request.method == "POST":
        kind = (request.form.get("type") or "").lower()
        try:
            if kind == "sum":
                raw = (request.form.get("args") or "").strip()
                for s in [",", ";"]:
                    raw = raw.replace(s, " ")
                nums = [x for x in raw.split(" ") if x.strip() != ""]
                args = [float(x) for x in nums]
                task = {"name": "sum", "args": args}
            elif kind == "upper":
                task = {"name": "upper", "s": request.form.get("s", "")}
            elif kind == "lower":
                task = {"name": "lower", "s": request.form.get("s", "")}
            else:
                error = "Tipo de tarea desconocido (sum | upper | lower)"
                return render_template("tareas.html", result=result, error=error)

            r = socket_rpc("TASK", {"task": task})
            if r.get("ok"):
                result = r.get("result")
            else:
                error = r.get("error")
        except Exception as e:
            error = str(e)

    return render_template("tareas.html", result=result, error=error)

# --- Alias ---
@app.get("/lab")
@login_required
def lab_alias():
    return redirect(url_for("tareas"))

# --- Main ---
if __name__ == "__main__":
    app.run(host=FLASK_HOST, port=FLASK_PORT, debug=FLASK_DEBUG)