"""Run an isolated, local MySQL demo without changing an installed MySQL service."""

import os
import secrets
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

import MySQLdb
from dotenv import dotenv_values
from MySQLdb import _mysql

PROJECT = Path(__file__).resolve().parents[1]
LOCAL = PROJECT / ".local"
LOCAL.mkdir(exist_ok=True)
env_path = PROJECT / ".env"
if not env_path.exists():
    env_path.write_text(
        f"SECRET_KEY={secrets.token_urlsafe(64)}\nDEBUG=True\n"
        "ALLOWED_HOSTS=localhost,127.0.0.1\nDB_NAME=labour_connect\n"
        f"DB_USER=labour_app\nDB_PASSWORD={secrets.token_urlsafe(32)}\n"
        "DB_HOST=127.0.0.1\nDB_PORT=3307\nGOOGLE_MAPS_API_KEY=\n"
        "EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend\n",
        encoding="utf-8",
    )
values = dotenv_values(env_path)
if (
    values.get("DB_NAME") != "labour_connect"
    or values.get("DB_PORT") != "3307"
    or values.get("DB_USER") != "labour_app"
):
    raise SystemExit(
        "Start-Demo expects DB_NAME=labour_connect, DB_USER=labour_app and DB_PORT=3307. For your own MySQL server, use python manage.py runserver instead."
    )
if (
    not values.get("DB_PASSWORD")
    or values.get("DB_PASSWORD") == "replace-with-your-database-password"
):
    raise SystemExit(
        "Set DB_PASSWORD to a unique password in .env, or remove the sample .env before the first demo launch."
    )
host = values.get("DB_HOST", "127.0.0.1")
if host not in ("127.0.0.1", "localhost", socket.gethostbyname(socket.gethostname())):
    raise SystemExit(
        "The isolated demo must bind a local interface. Use the normal Django command for a remote database."
    )
mysql_exe = os.environ.get("MYSQLD_PATH")
if not mysql_exe:
    candidates = sorted(
        Path(os.environ.get("ProgramFiles", "C:/Program Files")).glob(
            "MySQL/MySQL Server */bin/mysqld.exe"
        )
    )
    if not candidates:
        raise SystemExit(
            "MySQL Server 8.0.11+ is required. Install MySQL or set MYSQLD_PATH to mysqld.exe."
        )
    mysql_exe = str(candidates[-1])
data_path = LOCAL / "mysql"
if not (data_path / "auto.cnf").exists():
    data_path.mkdir(exist_ok=True)
    subprocess.run(
        [mysql_exe, "--no-defaults", "--initialize-insecure", f"--datadir={data_path}"],
        check=True,
    )


def literal(value):
    return "'" + _mysql.escape_string(str(value).encode()).decode() + "'"


sql_path = LOCAL / "initialize.sql"
account = f"'labour_app'@{literal(host)}"
sql_path.write_text(
    "CREATE DATABASE IF NOT EXISTS labour_connect CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;\n"
    f"CREATE USER IF NOT EXISTS {account} IDENTIFIED BY {literal(values['DB_PASSWORD'])};\n"
    f"GRANT ALL PRIVILEGES ON labour_connect.* TO {account};\n"
    f"GRANT ALL PRIVILEGES ON test_labour_connect.* TO {account};\n"
    f"ALTER USER 'root'@'localhost' IDENTIFIED BY {literal(secrets.token_urlsafe(40))};\n",
    encoding="utf-8",
)
mysql_log = (LOCAL / "mysql.log").open("w", encoding="utf-8")
web_server = None
server = subprocess.Popen(
    [
        mysql_exe,
        "--no-defaults",
        f"--datadir={data_path}",
        f"--bind-address={host}",
        "--port=3307",
        "--mysqlx=OFF",
        "--skip-name-resolve",
        f"--init-file={sql_path}",
        "--console",
    ],
    stdout=mysql_log,
    stderr=subprocess.STDOUT,
)
try:
    for attempt in range(30):
        if server.poll() is not None:
            raise SystemExit(
                "MySQL did not start. Read .local/mysql.log; another process may already use port 3307."
            )
        try:
            connection = MySQLdb.connect(
                host=host,
                port=3307,
                user="labour_app",
                passwd=values["DB_PASSWORD"],
                db="labour_connect",
                connect_timeout=2,
            )
            connection.close()
            break
        except MySQLdb.OperationalError:
            time.sleep(1)
    else:
        raise SystemExit("MySQL did not become ready. Read .local/mysql.log.")
    sql_path.unlink(missing_ok=True)
    for args in (
        ["migrate", "--noinput"],
        ["seed_demo"],
        ["check", "--database", "default"],
    ):
        subprocess.run([sys.executable, "manage.py", *args], cwd=PROJECT, check=True)
    web_host = "127.0.0.1" if host == "localhost" else host
    print(
        f"\nLabour Connect: http://{web_host}:8000/\nDemo passwords: {PROJECT / 'demo_accounts.txt'}\nPress Ctrl+C to stop the application and its isolated database.\n",
        flush=True,
    )
    web_server = subprocess.Popen(
        [sys.executable, "manage.py", "runserver", f"{web_host}:8000", "--noreload"],
        cwd=PROJECT,
    )
    if "--check-startup" in sys.argv:
        for attempt in range(30):
            try:
                with urllib.request.urlopen(
                    f"http://{web_host}:8000/", timeout=2
                ) as response:
                    if response.status == 200:
                        print(
                            "Startup verified: MySQL, migrations, seed, system checks and HTTP 200.",
                            flush=True,
                        )
                        break
            except OSError:
                time.sleep(1)
        else:
            raise SystemExit("Django did not become ready for the startup check.")
    else:
        web_server.wait()
except KeyboardInterrupt:
    pass
finally:
    sql_path.unlink(missing_ok=True)
    if web_server is not None and web_server.poll() is None:
        web_server.terminate()
        web_server.wait(timeout=20)
    if server.poll() is None:
        server.terminate()
        server.wait(timeout=20)
    mysql_log.close()
