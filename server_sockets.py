import os
import socket
import threading
import json
from concurrent.futures import ThreadPoolExecutor
from dotenv import load_dotenv

# --- Carga .env ---
load_dotenv()

from core.db import init_db
from core.auth import registrar_usuario, verificar_credenciales

# --- Configuración ---
HOST = os.getenv("SOCKET_HOST", "127.0.0.1")
PORT = int(os.getenv("SOCKET_PORT", "6000"))
MAX_CLIENTS = 100
WORKERS = int(os.getenv("WORKERS", "8"))

# --- HTML de bienvenida ---
WELCOME_HTML = """
<!doctype html>
<title>Inicio</title>
<h1>Inicio</h1>
<p>¡Bienvenido, {username}! (pool={pool})</p>
""".strip()

# --- Tareas soportadas (sum, upper, lower) ---
def execute_task(task: dict):
    if not isinstance(task, dict):
        raise ValueError("task must be an object")

    name = (task.get("name") or "").lower()

    if name == "sum":
        nums = task.get("args", [])
        if not isinstance(nums, list):
            raise ValueError("sum.args must be list")
        return sum(float(x) for x in nums)

    if name == "upper":
        s = task.get("s", "")
        return str(s).upper()

    if name == "lower":
        s = task.get("s", "")
        return str(s).lower()

    raise ValueError(f"unknown task name: {name}")

# --- Router ---
def handle_message(msg: dict) -> dict:
    op = (msg.get("op") or "").upper()
    data = msg.get("data") or {}

    if op == "TASK":
        task = data.get("task") or msg.get("task")
        res = execute_task(task)
        return {"ok": True, "result": res}

    if op == "REGISTRO":
        ok, info = registrar_usuario(data.get("username"), data.get("password"))
        return {"ok": ok, "info": info}

    if op == "LOGIN":
        ok = verificar_credenciales(data.get("username"), data.get("password"))
        return {"ok": ok}

    if op == "GET_TAREAS_HTML":
        u, p = data.get("username"), data.get("password")
        if not verificar_credenciales(u, p):
            return {"ok": False, "error": "401 Unauthorized"}
        return {"ok": True, "html": WELCOME_HTML.format(username=u, pool=WORKERS)}

    return {"ok": False, "error": f"op desconocida: {op}"}

# --- Loop por conexión ---
def client_thread(conn: socket.socket, addr, executor: ThreadPoolExecutor):
    MAX_BUFFER = 2 * 1024 * 1024

    with conn:
        buf = b""
        while True:
            try:
                chunk = conn.recv(4096)
            except ConnectionResetError:
                break
            if not chunk:
                break

            buf += chunk
            if len(buf) > MAX_BUFFER:
                conn.sendall((json.dumps({"ok": False, "error": "Request demasiado grande"}) + "\n").encode())
                break

            while b"\n" in buf:
                line, buf = buf.split(b"\n", 1)
                if not line.strip():
                    continue
                try:
                    req = json.loads(line.decode("utf-8"))
                except Exception:
                    conn.sendall((json.dumps({"ok": False, "error": "JSON inválido"}) + "\n").encode())
                    continue

                try:
                    resp = executor.submit(handle_message, req).result()
                except Exception as e:
                    resp = {"ok": False, "error": f"Error interno: {e}"}

                conn.sendall((json.dumps(resp) + "\n").encode())

# --- Main ---
def main():
    init_db()

    with ThreadPoolExecutor(max_workers=WORKERS) as executor:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind((HOST, PORT))
            s.listen(MAX_CLIENTS)
            s.settimeout(0.5)
            print(f"Servidor sockets en {HOST}:{PORT} (pool={WORKERS})")

            try:
                while True:
                    try:
                        conn, addr = s.accept()
                    except socket.timeout:
                        continue
                    threading.Thread(target=client_thread, args=(conn, addr, executor), daemon=True).start()
            except KeyboardInterrupt:
                print("\n[server] Ctrl+C recibido. Cerrando limpio...")

if __name__ == "__main__":
    main()