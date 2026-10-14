"""Start this project's existing MySQL data and Django together (no reseeding)."""
import json
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread

import MySQLdb
from dotenv import dotenv_values

PROJECT = Path(__file__).resolve().parents[1]
VALUES = dotenv_values(PROJECT / '.env')
VIEW_FILE = PROJECT.parent / 'database-preview.html'


def connect():
    return MySQLdb.connect(host='127.0.0.1', port=3307,
        user=VALUES['DB_USER'], passwd=VALUES['DB_PASSWORD'],
        db=VALUES['DB_NAME'], charset='utf8mb4', connect_timeout=3)


def snapshot():
    connection = connect()
    connection.query('SET SESSION TRANSACTION READ ONLY')
    cursor = connection.cursor()
    cursor.execute('SHOW TABLES')
    names = [r[0] for r in cursor.fetchall()]
    result = []
    for name in names:
        quoted = '`' + name.replace('`', '``') + '`'
        cursor.execute(f'SELECT COUNT(*) FROM {quoted}')
        count = cursor.fetchone()[0]
        cursor.execute(f'SHOW COLUMNS FROM {quoted}')
        columns = [{'name': row[0], 'type': row[1]} for row in cursor.fetchall()]
        visible = [c['name'] for c in columns if c['name'] not in ('password', 'session_key', 'session_data')]
        cursor.execute('SELECT ' + ', '.join('`' + c.replace('`', '``') + '`' for c in visible) + f' FROM {quoted} LIMIT 200')
        rows = [[None if v is None else str(v) for v in row] for row in cursor.fetchall()]
        result.append({'name': name, 'count': count, 'columns': columns, 'visible': visible, 'rows': rows})
    connection.close()
    return result


def make_html():
    data = json.dumps(snapshot(), ensure_ascii=True).replace('<', '\\u003c')
    template = (PROJECT / 'scripts' / 'database_view.html').read_text(encoding='utf-8')
    return template.replace('__DATABASE_DATA__', data)


class Viewer(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.split('?')[0] != '/':
            self.send_error(404)
            return
        try:
            body = make_html().encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Cache-Control', 'no-store')
            self.end_headers()
            self.wfile.write(body)
        except Exception:
            self.send_error(503, 'Database unavailable')


def main():
    mysql_exe = os.getenv('MYSQLD_PATH', r'C:\Program Files\MySQL\MySQL Server 8.4\bin\mysqld.exe')
    local = PROJECT / '.local'
    local.mkdir(exist_ok=True)
    mysql_log = (local / 'mysql-local.log').open('w', encoding='utf-8')
    web = None
    viewer = None
    server = subprocess.Popen([mysql_exe, '--no-defaults',
        f'--datadir={local / "mysql"}', '--bind-address=127.0.0.1', '--port=3307',
        '--mysqlx=OFF', '--skip-name-resolve', '--skip-log-bin',
        f'--pid-file={local / "mysql-current.pid"}', '--console'],
        cwd=PROJECT, stdout=mysql_log, stderr=subprocess.STDOUT)
    try:
        for attempt in range(30):
            if server.poll() is not None:
                raise RuntimeError('MySQL failed to start. Read .local/mysql-local.log.')
            try:
                connection = connect()
                connection.close()
                break
            except MySQLdb.Error:
                time.sleep(1)
        else:
            raise RuntimeError('MySQL connection failed. Check .env and .local/mysql-local.log.')
        env = dict(os.environ, DB_HOST='127.0.0.1', DB_PORT='3307')
        subprocess.run([sys.executable, 'manage.py', 'check', '--database', 'default'], cwd=PROJECT, env=env, check=True)
        subprocess.run([sys.executable, 'manage.py', 'migrate', '--check'], cwd=PROJECT, env=env, check=True)
        html = make_html()
        VIEW_FILE.write_text(html, encoding='utf-8')
        for table in snapshot():
            print(f"{table['name']}: {table['count']} rows", flush=True)
        viewer = ThreadingHTTPServer(('127.0.0.1', 8765), Viewer)
        Thread(target=viewer.serve_forever, daemon=True).start()
        web = subprocess.Popen([sys.executable, 'manage.py', 'runserver', '127.0.0.1:8000', '--noreload'], cwd=PROJECT, env=env)
        for attempt in range(30):
            try:
                with urllib.request.urlopen('http://127.0.0.1:8000/', timeout=2) as response:
                    print('Website HTTP:', response.status, flush=True)
                break
            except OSError:
                time.sleep(1)
        else:
            raise RuntimeError('Website failed to respond.')
        print(f'Website: http://127.0.0.1:8000/\nDatabase viewer: http://127.0.0.1:8765/\nSaved preview: {VIEW_FILE}\nPress Ctrl+C to stop.', flush=True)
        if '--check-startup' not in sys.argv:
            web.wait()
    except KeyboardInterrupt:
        pass
    finally:
        if viewer:
            viewer.shutdown()
            viewer.server_close()
        if web and web.poll() is None:
            web.terminate()
            web.wait(timeout=15)
        if server.poll() is None:
            try:
                connection = connect()
                connection.shutdown()
                connection.close()
                server.wait(timeout=15)
            except Exception:
                server.terminate()
                server.wait(timeout=15)
        mysql_log.close()


if __name__ == '__main__':
    main()
