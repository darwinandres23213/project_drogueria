#!/bin/sh
set -e

should_wait_for_mysql() {
  engine="${DB_ENGINE:-}"
  case "$engine" in
    *mysql*) return 0 ;;
  esac
  return 1
}

if [ "${SKIP_DB_WAIT:-0}" != "1" ] && should_wait_for_mysql; then
  echo "Esperando MySQL en ${DB_HOST:-db}:${DB_PORT:-3306}..."

  python << 'PY'
import os
import time
from pathlib import Path

import MySQLdb

host = os.getenv("DB_HOST", "db")
port = int(os.getenv("DB_PORT", "3306"))
user = os.getenv("DB_USER", "drogueria")
password = os.getenv("DB_PASSWORD", "drogueria")
database = os.getenv("DB_NAME", "drogueria")

kwargs = {
    "host": host,
    "port": port,
    "user": user,
    "passwd": password,
    "db": database,
    "connect_timeout": 3,
}

ssl_ca = os.getenv("DB_SSL_CA")
if ssl_ca:
    ca_path = Path(ssl_ca)
    if not ca_path.is_absolute():
        ca_path = Path("/app") / ca_path
    kwargs["ssl"] = {"ca": str(ca_path.resolve())}

for attempt in range(1, 31):
    try:
        conn = MySQLdb.connect(**kwargs)
        conn.close()
        print(f"MySQL listo (intento {attempt})")
        break
    except Exception as exc:
        print(f"MySQL no disponible ({attempt}/30): {exc}")
        time.sleep(2)
else:
    raise SystemExit("No se pudo conectar a MySQL")
PY
fi

echo "Aplicando migraciones..."
python manage.py migrate --noinput --fake-initial

echo "Collectstatic..."
python manage.py collectstatic --noinput || true

echo "Iniciando aplicación..."
exec "$@"
