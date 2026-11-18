# Web contra la violencia de género · 25N

Aplicación Flask para el 25N: el público deja mensajes desde el móvil (QR → `/participa`),
una persona moderadora los revisa en `/admin` (con ayuda de un filtro automático) y una
pantalla proyectada (`/pantalla`) va rotando entre el mural de burbujas, el vídeo y las
reflexiones del foro.

Las tareas están en [`docs/tareas/`](docs/tareas/).

## Estructura de carpetas

Cada archivo ya existe con un comentario que indica qué tarea lo rellena.
**No crees archivos fuera de esta estructura sin comentarlo antes con el equipo.**

```
.
├── app.py                  T01–T03 · rutas Flask (sin SQL: se usa bd/db.py)
├── wsgi.py                 T05 · entrada de producción (gunicorn)
├── bd/
│   ├── db.py               Acceso a la base de datos (todas las consultas)
│   ├── schema.sql          Tablas mural y foro (+ filtros y ajustes de T03)
│   ├── filtro.py           T03 · filtro automático de palabras y datos personales
│   └── filtros_iniciales.txt  T03 · lista de palabras con la que arranca el filtro
├── templates/              Plantillas Jinja (HTML)
│   ├── participa.html      T06 · formulario público
│   ├── gracias.html        T06 · confirmación
│   ├── admin.html          T03 · panel de moderación
│   └── pantalla.html       T04/T07/T08/T09/T10 · esqueleto común de la pantalla
├── static/
│   ├── css/
│   │   ├── estilos.css     T10 · estilos de la pantalla
│   │   ├── mural.css       T07 · mural de burbujas (lo carga mural.js)
│   │   ├── video.css       T08 · vista de vídeo (lo carga video.js)
│   │   ├── participa.css   T06 · estilos del formulario
│   │   └── admin.css       T03 · estilos del panel
│   ├── js/
│   │   ├── participa.js    T06 · contador de caracteres del formulario
│   │   ├── admin.js        T03 · filtros, búsqueda, novedades y confirmación del panel
│   │   ├── pantalla.js     T04 · rotación de vistas y actualización
│   │   ├── mural.js        T07 · pintarMural(mensajes)
│   │   ├── video.js        T08 · iniciarVideo() / pararVideo()
│   │   └── foro.js         T09 · pintarForo(reflexiones)
│   ├── fonts/              T07 · fuentes del mural en local (woff2, OFL)
│   ├── img/qr.png          T10 · QR de /participa
│   └── video/video.mp4     T08 · vídeo de concienciación
├── deploy/                 T05 · scripts y plantillas de despliegue
├── docs/
│   ├── tareas/             Enunciado de cada tarea (T01–T10)
│   ├── t10/                T10 · vista previa de estilos.css y lista de pruebas en móviles
│   └── DESPLIEGUE.md       T05 · guía de despliegue y checklist de PRs
├── herramientas/
│   └── generar_qr.py       T10 · regenera static/img/qr.png (sin dependencias)
├── datos/                  Se crea solo: aquí vive 25n.db (no se sube a git)
├── requirements.txt
└── .env.example            Variables de entorno (copiar a .env)
```

## Puesta en marcha

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # y rellena las contraseñas
python -m bd.db             # crea datos/25n.db
flask --app app run --debug
```

En producción la app corre con gunicorn detrás de NGINX en
**https://thedevhub.santiagof.dev/colaboraciones/2026-2027/web-contra-la-violencia-de-genero/**.
Ver [`docs/DESPLIEGUE.md`](docs/DESPLIEGUE.md).

## URLs: la app vive en un subdirectorio

En producción todas las rutas llevan delante `/colaboraciones/2026-2027/web-contra-la-violencia-de-genero`.
Por eso **nunca se escriben rutas que empiecen por `/`**:

- **Plantillas:** siempre `url_for`.
  `<form method="POST" action="{{ url_for('crear_mural') }}">`,
  `<link href="{{ url_for('static', filename='css/estilos.css') }}">`
- **Python:** `redirect(url_for('gracias'))`, nunca `redirect('/gracias')`.
- **JavaScript:** las URLs las da la plantilla. `pantalla.html` las pone en `<body data-api-mural="…">`
  y el JS las lee con `document.body.dataset.apiMural`.

Nombres de las rutas (el nombre de la función en `app.py` = endpoint de `url_for`):

| Endpoint | Ruta | Método | Tarea |
|---|---|---|---|
| `inicio` | `/` → redirige a `participa` | GET | T01 |
| `participa` | `/participa` | GET | T01 |
| `crear_mural` | `/mural` | POST | T01 |
| `crear_foro` | `/foro` | POST | T01 |
| `gracias` | `/gracias` | GET | T01 |
| `pantalla` | `/pantalla` | GET | T02 |
| `api_mural` | `/api/mural` | GET | T02 |
| `api_foro` | `/api/foro` | GET | T02 |
| `admin` | `/admin` | GET | T03 |
| `admin_accion` | `/admin/<tabla>/<int:id>/<accion>` | POST | T03 |
| `admin_estado` | `/admin/estado` (contadores en JSON) | GET | T03 |
| `admin_filtro_anadir` | `/admin/filtros` | POST | T03 |
| `admin_filtro_quitar` | `/admin/filtros/<int:id>/borrar` | POST | T03 |
| `admin_ajustes` | `/admin/ajustes` | POST | T03 |

Usuarios de HTTP Basic Auth: `admin` y `pantalla` (variables `ADMIN_USER`/`PANTALLA_USER` en `.env`),
con las contraseñas `ADMIN_PASS` y `PANTALLA_PASS`.

## Moderación (T03)

- **Foro:** por defecto las reflexiones **no salen hasta que moderación las aprueba** en `/admin`
  («Pendientes de revisar»), porque pueden contar casos reales con nombres o lugares.
  Relajarlo (que se publiquen solas si pasan el filtro) es una decisión del equipo desde el panel.
- **Filtro automático** (`bd/filtro.py`): los mensajes del mural se publican solos salvo los que
  contienen una palabra de la lista o datos personales (enlaces, correos, teléfonos, @usuarios).
  Esos quedan pendientes en `/admin` para publicarlos igualmente o borrarlos. El filtro entiende
  tildes, plurales, mayúsculas y trucos (`z0rra`, `p.u.t.a`); con `*` al final cubre todo lo que
  empiece igual. La lista y las reglas se cambian desde el panel; la primera vez se carga
  `bd/filtros_iniciales.txt`. El filtro **no** detecta nombres ni lugares.
- Los formularios del panel llevan un token CSRF derivado de `ADMIN_PASS`.
- Una base de datos creada antes de T03 se actualiza sola al arrancar (`init_db()` añade lo que falte).

## Normas del equipo

1. **Una rama por tarea**, creada desde `main`: `t01-backend-base`, `t07-mural-burbujas`…
   Nunca se trabaja directamente en `main`. Se integra con una Pull Request.
2. **Toca solo los archivos de tu tarea.** En `pantalla.html` cada tarea rellena únicamente su
   `<section>` o bloque marcado; no reordenes lo demás.
3. **Base de datos:** solo desde `bd/db.py`, con consultas parametrizadas (`?`).
   Si necesitas una consulta nueva, añádela allí como función.
4. **Texto de usuario en JavaScript:** siempre `textContent`, nunca `innerHTML`.
5. **Contraseñas:** solo en `.env` (que no se sube). Nada de claves en el código.
6. **Nombres** en español y sin tildes en archivos, funciones y variables
   (`pintarMural`, `listar_foro`, `vista-mural`).
7. **Nunca rutas absolutas** (ver «URLs» arriba): `url_for` en plantillas y Python; en JS, las URLs de `data-*`.
8. **Sin JavaScript ni CSS en línea:** nada de `<script>…</script>`, `<style>`, `onclick=` ni `style=` en el HTML.
   Todo va en `static/js/` y `static/css/` (el servidor puede bloquearlo por seguridad).
