# PFO3 — Cliente web (Flask) + Servidor TCP con workers + PostgreSQL (DB en Docker)

Implementación:

- **Cliente**: gateway web en **Flask** (presentación).
- **Servidor**: servicio **TCP por sockets** que **recibe tareas** y las **distribuye** a un **pool de workers** (concurrency).
- **Protocolo**: **JSON por línea** (`\n` al final) entre cliente y servidor.
- **Persistencia**: **PostgreSQL** en Docker (usuarios/registro/login).

---

- **Cliente envía tareas y recibe resultados**: la vista **/tareas** en Flask manda `{"op":"TASK","task":{...}}` por socket y muestra la respuesta.
- **Servidor recibe tareas y distribuye a workers**: `server_sockets.py` usa `ThreadPoolExecutor` para correr cada tarea en un hilo del pool.
- **Arquitectura distribuida**: separación clara entre presentación (Flask), lógica (servidor TCP) y datos (PostgreSQL).

```
Navegador ──HTTP──► Flask (cliente)
                    │
                    └──TCP(JSON)──► Servidor Sockets (workers)
                                      │
                                      └──► PostgreSQL (Docker)
```

---

## ✅ Requisitos previos
- **Python 3.10+**
- **pip**
- **Docker** (Desktop/Engine) con **docker compose**
- **Git**

> Windows: se recomienda PowerShell o CMD. En Git Bash, Ctrl+C a veces no corta procesos Python.

---

## 📦 Estructura del proyecto
```
PFO3_PSR/
├─ core/
│  ├─ db.py                 # conexión a PostgreSQL e init de schema
│  └─ auth.py               # registrar_usuario / verificar_credenciales
├─ server_sockets.py        # servidor TCP + pool de workers (sum/upper/lower)
├─ http_gateway.py          # Flask (cliente web) que llama por sockets
├─ templates/
│  ├─ base.html
│  ├─ inicio.html
│  ├─ login.html
│  ├─ register.html
│  └─ tareas.html           # UI para enviar tareas al servidor
├─ static/
│  └─ styles.css
├─ docker-compose.yml       # PostgreSQL + Adminer
├─ requirements.txt
└─ .env                     # variables de entorno
```

---

## ⚙️ Configuración (.env)
Ejemplo funcional:

# Flask
SECRET_KEY=ClaveSecreta123
FLASK_HOST=127.0.0.1
FLASK_PORT=5000
FLASK_DEBUG=true

# Sockets
SOCKET_HOST=127.0.0.1
SOCKET_PORT=6000
WORKERS=8

# PostgreSQL (Docker local)
DATABASE_URL=postgresql://pfo3user:pfo3pass@127.0.0.1:5432/pfo3db

> Cambiar puertos si están ocupados. Si usás `FLASK_DEBUG=false`, la app de Flask no recarga automáticamente.

---

## 🚀 Pasos para ejecutar

1) **Clonar o descomprimir** el proyecto y entrar a la carpeta del repo.

2) **Instalar dependencias**:
```bash
pip install -r requirements.txt
```

3) **Levantar la base de datos** (Docker):
```bash
docker compose up -d db adminer
```
- Adminer: http://localhost:8080  
  - System: PostgreSQL  
  - Server: `db`  
  - User: `pfo3user`  
  - Password: `pfo3pass`  
  - Database: `pfo3db`

4) **Iniciar el servidor de sockets** (backend):
```bash
python server_sockets.py
```
Deberías ver: `Servidor sockets en 127.0.0.1:6000 (pool=8)`

5) **Iniciar el gateway web** (otra terminal):
```bash
python http_gateway.py
```

6) **Usar la app**:
- Abrí: http://127.0.0.1:5000  
- Registrate → Login → **Inicio** (HTML generado por el servidor por sockets).  
- Ir a **Tareas**: probar `sum`, `upper` y `lower`.

---

## 🛰️ Protocolo (Cliente ⇄ Servidor de sockets)

- Transporte: **TCP**
- Formato: **JSON por línea** (`\n` al final)

### Operaciones
- **TASK** (tareas soportadas: `sum`, `upper`, `lower`)
  - Solicitud:
    ```json
    {"op":"TASK","data":{"task":{"name":"sum","args":[1,2,3.5]}}}
    ```
    ```json
    {"op":"TASK","data":{"task":{"name":"upper","s":"hola"}}}
    ```
    ```json
    {"op":"TASK","data":{"task":{"name":"lower","s":"HOLA"}}}
    ```
  - Respuesta:
    ```json
    {"ok": true, "result": 6.5}
    ```
    ```json
    {"ok": true, "result": "HOLA"}
    ```
    ```json
    {"ok": true, "result": "hola"}
    ```

- **REGISTRO** / **LOGIN** / **GET_TAREAS_HTML**: usadas por el gateway para autenticación e inicio.

---

## 🔧 Comandos útiles

- **Ver estado de contenedores**:
```bash
docker compose ps
```

- **Recrear DB limpia** (borra datos):
```bash
docker compose down -v
docker compose up -d db adminer
```

- **Liberar puerto ocupado (Windows)**:
```bat
netstat -ano | findstr :6000
taskkill /PID <PID> /F
```

- **Cortar el servidor de sockets**: `Ctrl+C`.  
  (El server usa `settimeout(0.5)` para responder rápido al Ctrl+C.)

---

## 🧪 Pruebas rápidas / Concurrencia
Abrí dos pestañas en **/tareas**:
- En una: `sum` con muchos números.
- En otra: `upper` o `lower` repetidamente.

Vas a ver respuestas independientes y concurrentes, gestionadas por el pool (`WORKERS=8`). Si ponés `WORKERS=1`, se serializa todo (útil para demostrar el efecto del pool).

---

## 🆘 Troubleshooting

**FATAL: password authentication failed**  
- Asegurate de estar conectando al Postgres del contenedor. Si hay un Postgres local en 5432, cambiá el **mapeo** del compose a `5433:5432` y ajustá `DATABASE_URL` a puerto `5433`.

**`DATABASE_URL no configurada`**  
- Revisá que `.env` exista en la raíz y que `python-dotenv` lo cargue (se hace al inicio de cada proceso).

**No corta con Ctrl+C**  
- Usá PowerShell o CMD (en Git Bash a veces no entra la señal). El server ya tiene timeout en `accept()`.

**Adminer no conecta**  
- Probar con **Server: `db`** dentro de Adminer. Si seguís con error, esperá el `healthcheck` o reiniciá: `docker compose restart db`.

---