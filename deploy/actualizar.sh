#!/usr/bin/env bash
# Actualiza el servidor con lo último de main (T05).
#
#   cd <carpeta del proyecto en el servidor>
#   bash deploy/actualizar.sh [url_base_para_comprobar]
set -euo pipefail
export PIP_USER=0   # por si el servidor fuerza instalaciones --user (rompe el venv)

APP_DIR="$(cd "$(dirname "$0")/.." && pwd)"
SERVICIO=25n-web
cd "$APP_DIR"

echo "==> Descargando cambios de main"
git checkout --quiet main
git pull --ff-only origin main

echo "==> Dependencias"
.venv/bin/pip install --quiet -r requirements.txt
.venv/bin/pybabel compile -d traducciones >/dev/null   # idiomas (i18n): .po → .mo

echo "==> Base de datos (crea lo que falte, no borra nada)"
set -a; . ./.env; set +a
.venv/bin/python -m bd.db

echo "==> Reiniciando $SERVICIO"
sudo systemctl restart "$SERVICIO"
sleep 2
systemctl is-active --quiet "$SERVICIO" || {
    echo "El servicio no ha arrancado. Últimas líneas del log:"
    journalctl -u "$SERVICIO" -n 30 --no-pager
    exit 1
}

bash deploy/comprobar.sh "${1:-http://127.0.0.1:8256}"
