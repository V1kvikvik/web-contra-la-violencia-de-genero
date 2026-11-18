# Despliegue (T05)

URL pública: **https://thedevhub.santiagof.dev/colaboraciones/2026-2027/web-contra-la-violencia-de-genero/**
URL del QR (T10): **https://thedevhub.santiagof.dev/colaboraciones/2026-2027/web-contra-la-violencia-de-genero/participa**

```
Móvil / pantalla ──HTTPS──▶ NGINX (443)
                              ├─ …/static/*  → archivos de static/ (los sirve NGINX directamente)
                              └─ …/*         → gunicorn 127.0.0.1:8256 → wsgi.py → app.py → bd/db.py → datos/25n.db
```

| Archivo | Para qué |
|---|---|
| `wsgi.py` | Entrada de gunicorn. Aplica `ProxyFix` para que `url_for` añada el prefijo del subdirectorio. |
| `deploy/gunicorn.conf.py` | Puerto 8256 (solo local), 2 procesos × 4 hilos. |
| `deploy/25n-web.service` | Plantilla del servicio systemd (`25n-web`). |
| `deploy/nginx-location.conf` | Plantilla del fragmento de NGINX. |
| `deploy/instalar.sh` | Primera instalación. Se puede repetir sin problema. |
| `deploy/actualizar.sh` | Baja `main`, reinicia el servicio y lanza las pruebas. |
| `deploy/comprobar.sh` | Pruebas de humo: códigos HTTP, autenticación y prefijo en los formularios. |

## 1. Primera instalación (en el servidor)

```bash
git clone https://github.com/thedevhub-uea/web-contra-la-violencia-de-genero.git <carpeta>
cd <carpeta>
cp .env.example .env && nano .env      # contraseñas largas y distintas para admin y pantalla
bash deploy/instalar.sh
```

El script comprueba Python ≥ 3.10, crea `.venv`, instala dependencias, crea la BD, instala y arranca
el servicio `25n-web`, y **muestra el fragmento de NGINX** con las rutas reales ya puestas.

Pega ese fragmento en el `server {}` del dominio, **antes** de `location /colaboraciones/`, y recarga NGINX:

```bash
sudo nginx -t && sudo systemctl reload nginx
```

> La configuración real de NGINX y las rutas del servidor **no se suben al repositorio**.

## 2. Actualizar tras fusionar PRs

```bash
cd <carpeta> && bash deploy/actualizar.sh https://thedevhub.santiagof.dev/colaboraciones/2026-2027/web-contra-la-violencia-de-genero
```

## 3. Checklist para revisar cada PR antes de fusionarla

- [ ] Solo toca los archivos de su tarea (ver README).
- [ ] SQL solo en `bd/db.py`, siempre con `?` (nada de f-strings ni `+` en consultas).
- [ ] Texto de usuario en JS con `textContent`, nunca `innerHTML`.
- [ ] Ninguna contraseña ni clave en el código; solo en `.env`.
- [ ] **Ninguna ruta absoluta**: en plantillas `url_for(...)`; en JS, las URLs que da la plantilla (`data-*`).
      Buscar: `grep -rnE "(href|src|action)=\"/|fetch\('/" templates static`
- [ ] Sin `<script>` ni `<style>` en línea ni atributos `onclick=`/`style=`: la cabecera CSP del servidor puede bloquearlos.
- [ ] Usa los nombres de endpoint del README.
- [ ] Textos visibles traducibles (`_()` en plantillas y Python, `data-textos` en JS) y
      `pybabel compile -d traducciones --statistics` al 100 % (ver README, «Idiomas»).
- [ ] Funciona en local: `flask --app app run --debug`.

## 4. Prueba completa (el día antes del evento)

1. `bash deploy/comprobar.sh <URL pública>` → «Todo correcto».
2. Escanear el QR desde **2–3 móviles con datos móviles** (sin wifi del centro), Android e iPhone.
3. Enviar un mensaje burbuja y una reflexión desde cada uno → aparece `/gracias`.
4. En `/admin` (credenciales de admin): ocultar un mensaje y aprobar una reflexión.
5. En la pantalla real (`/pantalla`, credenciales de pantalla, F11): el mensaje oculto desaparece en ≤ 10 s
   y la reflexión aprobada aparece; dejarla 15 min y comprobar que completa un ciclo entero con el vídeo.
6. `sudo systemctl restart 25n-web` → los mensajes siguen ahí (la BD persiste).
7. Escanear el QR desde 3–4 m en la pantalla real.

## 5. Durante el evento

```bash
journalctl -u 25n-web -f              # ver peticiones y errores en directo
sudo systemctl restart 25n-web        # si algo se queda colgado
systemctl status 25n-web
```

Si cae la app, la pantalla sigue mostrando los últimos datos (T04). El servicio se reinicia solo si gunicorn falla.
