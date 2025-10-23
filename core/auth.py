from werkzeug.security import generate_password_hash, check_password_hash
from .db import get_conn

# --- SQL ---
SQL_INS = "INSERT INTO usuarios (username, password_hash) VALUES (%s, %s)"
SQL_GET = "SELECT password_hash FROM usuarios WHERE username = %s"

# --- Funciones ---
def registrar_usuario(username: str, password: str) -> tuple[bool, str]:
    if not username or not password:
        return False, "username y password son requeridos"
    pwh = generate_password_hash(password)
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(SQL_INS, (username, pwh))
        return True, "ok"
    except Exception as e:
        if getattr(e, "sqlstate", None) == "23505":
            return False, "usuario ya existe"
        return False, str(e)

def verificar_credenciales(username: str, password: str) -> bool:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(SQL_GET, (username,))
            row = cur.fetchone()
    if not row:
        return False
    return check_password_hash(row[0], password)