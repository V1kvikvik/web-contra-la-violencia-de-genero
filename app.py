"""Aplicación Flask del proyecto 25N.

Responsables:
- T01: creación de la app, init de la BD, POST /mural, POST /foro, /participa, /gracias
- T02: decorador de HTTP Basic Auth, GET /api/mural, GET /api/foro, GET /pantalla
- T03: GET /admin y POST /admin/<tabla>/<id>/<accion>, más el filtro automático
       (/admin/filtros, /admin/ajustes) y los avisos del público (/avisar)

Toda la base de datos se usa a través de `bd.db` (no escribir SQL aquí).
"""

import hashlib
import hmac
import os
import re
import secrets
import threading
import time
from collections import defaultdict, deque
from datetime import datetime, timezone
from functools import wraps

from flask import Flask, Response, abort, jsonify, redirect, render_template, request, url_for

from bd import db


# --- T02: HTTP Basic Auth -----------------------------------------------------
# Usuarios y contraseñas solo desde variables de entorno (.env), nunca en el código.
# Rol "admin": /admin, /pantalla y /api/*. Rol "pantalla": /pantalla y /api/*.
# Si falta la contraseña de un rol, ese rol no puede entrar.

def _cuentas():
    """{usuario: (rol, contraseña)} leído en cada petición desde el entorno."""
    cuentas = {}
    for rol, var_usuario, var_pass in (
        ("admin", "ADMIN_USER", "ADMIN_PASS"),
        ("pantalla", "PANTALLA_USER", "PANTALLA_PASS"),
    ):
        usuario = os.environ.get(var_usuario) or rol
        password = os.environ.get(var_pass)
        if password:
            cuentas[usuario] = (rol, password)
    return cuentas


def _rol_autenticado():
    """Devuelve el rol de las credenciales Basic de la petición, o None."""
    auth = request.authorization
    if auth is None or auth.username is None or auth.password is None:
        return None
    cuenta = _cuentas().get(auth.username)
    if cuenta is None:
        return None
    rol, esperada = cuenta
    if hmac.compare_digest(auth.password.encode("utf-8"), esperada.encode("utf-8")):
        return rol
    return None


def requiere_rol(*roles):
    """Decorador: 401 salvo credenciales Basic válidas de uno de los roles indicados."""

    def decorador(vista):
        @wraps(vista)
        def envoltura(*args, **kwargs):
            if _rol_autenticado() not in roles:
                return Response(
                    "Acceso restringido",
                    401,
                    {"WWW-Authenticate": 'Basic realm="25N", charset="UTF-8"'},
                )
            return vista(*args, **kwargs)

        return envoltura

    return decorador


# --- T03: moderación ----------------------------------------------------------
# La moderación no aprueba uno por uno: el filtro automático (bd/filtro.py) decide qué
# se publica. El panel muestra lo que el filtro ha retenido y lo que el público ha
# avisado, gestiona la lista de palabras y las reglas, y puede retirar o borrar cualquier cosa.

def _token_csrf():
    """Token que llevan todos los formularios del panel.

    El navegador reenvía solo la autenticación Basic, así que otra web podría enviar
    formularios a /admin en nombre de la moderadora. Este token sale de la contraseña
    de admin (otra web no puede leerlo), así que esos envíos se rechazan.
    """
    usuario = os.environ.get("ADMIN_USER") or "admin"
    clave = os.environ.get("ADMIN_PASS", "")
    return hmac.new(clave.encode("utf-8"), ("csrf-25n:" + usuario).encode("utf-8"),
                    hashlib.sha256).hexdigest()


def _comprobar_csrf():
    if not hmac.compare_digest(request.form.get("csrf", ""), _token_csrf()):
        abort(403)


# Aviso que se muestra en el panel tras cada acción (?hecho=objeto.accion.id&n=retirados).
# Son textos fijos: de la dirección solo se toman números.
_AVISOS_PANEL = {
    ("mural", "mostrar"): "Mensaje #{id} publicado. Se verá en la pantalla en la próxima actualización.",
    ("mural", "ocultar"): "Mensaje #{id} retirado de la pantalla.",
    ("mural", "borrar"): "Mensaje #{id} borrado.",
    ("foro", "aprobar"): "Reflexión #{id} publicada. Se verá en la pantalla en la próxima actualización.",
    ("foro", "retirar"): "Reflexión #{id} retirada de la pantalla.",
    ("foro", "borrar"): "Reflexión #{id} borrada.",
    ("filtro", "anadido"): "Añadido al filtro: «{termino}».{retirados}",
    ("filtro", "quitado"): "Término quitado del filtro.",
    ("filtro", "invalido"): "No se ha añadido: usa solo letras y espacios (de 2 a 60), con * al final si quieres.",
    ("filtro", "repetido"): "Ese término ya estaba en el filtro.",
    ("ajustes", "guardados"): "Ajustes guardados.{retirados}",
}
_AVISOS_ERROR = {("filtro", "invalido"), ("filtro", "repetido")}
_ANCLA_PANEL = {"mural": "revision", "foro": "revision", "filtro": "filtro", "ajustes": "filtro"}
_HECHO = re.compile(r"^([a-z]+)\.([a-z]+)\.(\d{1,12})$")


def _volver_al_panel(objeto, accion, id_=0, retirados=0):
    parametros = {"hecho": "%s.%s.%d" % (objeto, accion, id_)}
    if retirados:
        parametros["n"] = int(retirados)
    return redirect(url_for("admin", **parametros) + "#" + _ANCLA_PANEL[objeto], code=303)


def _ultima_accion():
    """Lee ?hecho=… y devuelve {texto, tipo, resaltar} para la plantilla, o None."""
    hecho = _HECHO.match(request.args.get("hecho", ""))
    if not hecho:
        return None
    objeto, accion, id_ = hecho.group(1), hecho.group(2), int(hecho.group(3))
    plantilla = _AVISOS_PANEL.get((objeto, accion))
    if plantilla is None:
        return None
    n = request.args.get("n", "")
    n = int(n) if n.isdigit() and len(n) < 7 else 0
    retirados = ""
    if n == 1:
        retirados = " Se ha retirado 1 publicación que ya estaba en pantalla."
    elif n > 1:
        retirados = " Se han retirado %d publicaciones que ya estaban en pantalla." % n
    termino = ""
    if (objeto, accion) == ("filtro", "anadido"):
        termino = db.termino_filtro(id_)
        if termino is None:
            return None
    return {
        "texto": plantilla.format(id=id_, termino=termino, retirados=retirados),
        "tipo": "error" if (objeto, accion) in _AVISOS_ERROR else "ok",
        "resaltar": "%s-%d" % (objeto, id_) if objeto in db.TABLAS and accion != "borrar" else None,
    }


def _zona_horaria():
    try:
        from zoneinfo import ZoneInfo
        return ZoneInfo(os.environ.get("ZONA_HORARIA") or "Europe/Madrid")
    except Exception:  # p. ej. Windows sin el paquete tzdata: hora local del equipo
        return None


def _fecha(valor):
    """Filtro de plantilla: "hoy, 10:42" o "17/11/2026 18:05" en hora de España.
    SQLite guarda `creado` en UTC."""
    if not valor:
        return ""
    try:
        momento = datetime.fromisoformat(str(valor))
    except ValueError:
        return str(valor)
    if momento.tzinfo is None:
        momento = momento.replace(tzinfo=timezone.utc)
    zona = _zona_horaria()
    local = momento.astimezone(zona)
    if local.date() == datetime.now(timezone.utc).astimezone(zona).date():
        return "hoy, " + local.strftime("%H:%M")
    return local.strftime("%d/%m/%Y %H:%M")


class Limitador:
    """Cuántas peticiones se permiten por IP en una ventana de tiempo (en memoria, por proceso)."""

    def __init__(self, maximo, segundos):
        self.maximo, self.segundos = maximo, segundos
        self._marcas = defaultdict(deque)
        self._cerrojo = threading.Lock()

    def permitir(self, clave):
        ahora = time.monotonic()
        with self._cerrojo:
            marcas = self._marcas[clave]
            while marcas and ahora - marcas[0] > self.segundos:
                marcas.popleft()
            if len(marcas) >= self.maximo:
                return False
            marcas.append(ahora)
            return True


def create_app():
    app = Flask(__name__)
    db.init_db()

    @app.get("/")
    def inicio():
        return redirect(url_for("participa"))

    @app.get("/participa")
    def participa():
        return render_template("participa.html")

    @app.post("/mural")
    def crear_mural():
        texto = request.form.get("texto", "").strip()
        if not texto:
            return render_template(
                "participa.html",
                error_message="Escribe un mensaje antes de enviarlo.",
            ), 400
        if len(texto) > db.MAX_MURAL_TEXTO:
            return render_template(
                "participa.html",
                error_message=(
                    f"El mensaje no puede superar los "
                    f"{db.MAX_MURAL_TEXTO} caracteres."
                ),
            ), 400

        db.insertar_mural(texto)
        return redirect(url_for("gracias"))

    @app.post("/foro")
    def crear_foro():
        titulo = request.form.get("titulo", "").strip()
        texto = request.form.get("texto", "").strip()

        if not titulo:
            error_message = "Escribe un título antes de enviar la reflexión."
        elif len(titulo) > db.MAX_FORO_TITULO:
            error_message = (
                f"El título no puede superar los "
                f"{db.MAX_FORO_TITULO} caracteres."
            )
        elif not texto:
            error_message = "Escribe una reflexión antes de enviarla."
        elif len(texto) > db.MAX_FORO_TEXTO:
            error_message = (
                f"La reflexión no puede superar los "
                f"{db.MAX_FORO_TEXTO} caracteres."
            )
        else:
            error_message = None

        if error_message:
            return render_template(
                "participa.html",
                error_message=error_message,
            ), 400

        db.insertar_foro(titulo, texto)
        return redirect(url_for("gracias"))

    @app.get("/gracias")
    def gracias():
        return render_template("gracias.html")

    # --- T02: pantalla y API JSON (solo contenido publicable) ---------------

    @app.get("/pantalla")
    @requiere_rol("admin", "pantalla")
    def pantalla():
        return render_template("pantalla.html")

    @app.get("/api/mural")
    @requiere_rol("admin", "pantalla")
    def api_mural():
        mensajes = db.listar_mural(solo_visibles=True, limite=30)
        return jsonify([{"id": m["id"], "texto": m["texto"]} for m in mensajes])

    @app.get("/api/foro")
    @requiere_rol("admin", "pantalla")
    def api_foro():
        reflexiones = db.listar_foro(solo_aprobadas=True)
        return jsonify(
            [{"id": r["id"], "titulo": r["titulo"], "texto": r["texto"]} for r in reflexiones]
        )

    # --- T03: panel de moderación (solo rol admin) --------------------------

    app.add_template_filter(_fecha, "fecha")

    @app.after_request
    def cabeceras_admin(resp):
        if (request.endpoint or "").startswith("admin"):
            resp.headers["Cache-Control"] = "no-store"
            resp.headers["X-Frame-Options"] = "DENY"
            resp.headers["Referrer-Policy"] = "same-origin"
        return resp

    @app.get("/admin")
    @requiere_rol("admin")
    def admin():
        aviso = _ultima_accion()
        return render_template(
            "admin.html",
            elementos=db.listar_para_panel(),
            terminos=db.listar_filtros(),
            ajustes=db.leer_ajustes(),
            csrf=_token_csrf(),
            aviso=aviso,
            resaltar=aviso["resaltar"] if aviso else None,
        )

    @app.get("/admin/estado")
    @requiere_rol("admin")
    def admin_estado():
        """Contadores en JSON: el panel avisa si llegan avisos o retenidos nuevos."""
        return jsonify(db.contadores())

    @app.post("/admin/<tabla>/<int:id>/<accion>")
    @requiere_rol("admin")
    def admin_accion(tabla, id, accion):
        _comprobar_csrf()
        try:
            db.aplicar_accion(tabla, id, accion)
        except ValueError:
            abort(404)
        return _volver_al_panel(tabla, accion, id)

    @app.post("/admin/filtros")
    @requiere_rol("admin")
    def admin_filtro_anadir():
        _comprobar_csrf()
        id_, error = db.anadir_filtro(request.form.get("termino", ""))
        if error:
            return _volver_al_panel("filtro", error)
        return _volver_al_panel("filtro", "anadido", id_, db.revisar_publicados())

    @app.post("/admin/filtros/<int:id>/borrar")
    @requiere_rol("admin")
    def admin_filtro_quitar(id):
        _comprobar_csrf()
        db.quitar_filtro(id)
        return _volver_al_panel("filtro", "quitado")

    @app.post("/admin/ajustes")
    @requiere_rol("admin")
    def admin_ajustes():
        _comprobar_csrf()
        nuevos = {regla: "1" if request.form.get(regla) == "1" else "0"
                  for regla in ("enlaces", "correos", "telefonos", "usuarios", "foro_manual",
                                "retirar_por_avisos")}
        umbral = request.form.get("avisos_para_ocultar", "")
        if umbral.isdigit() and 1 <= int(umbral) <= 50:
            nuevos["avisos_para_ocultar"] = str(int(umbral))
        db.guardar_ajustes(nuevos)
        return _volver_al_panel("ajustes", "guardados", 0, db.revisar_publicados())

    # --- T03: avisos del público (sin contraseña) ---------------------------
    # Quien vea en la pantalla algo inapropiado lo busca en /avisar y lo marca: aparece en
    # «Avisos del público» del panel. Solo se retira solo si se activa en el panel
    # (ajuste retirar_por_avisos, apagado por defecto).

    # Como mucho 60 avisos cada 10 minutos desde una misma IP (en un instituto
    # muchos móviles salen por la misma IP, por eso no es más bajo).
    limite_avisos = Limitador(60, 600)

    def pagina_avisar(error_message=None, codigo=200):
        return render_template(
            "avisar.html",
            mensajes=db.listar_mural(solo_visibles=True, limite=30),
            reflexiones=db.listar_foro(solo_aprobadas=True),
            enviado=request.args.get("enviado") == "1",
            retirada_automatica=db.leer_ajustes()["retirar_por_avisos"] == "1",
            error_message=error_message,
        ), codigo

    def huella_avisador(resp):
        """Cookie anónima para que un mismo móvil no cuente dos veces. Se guarda solo su hash."""
        valor = request.cookies.get("avisador", "")
        if len(valor) != 32 or not valor.isalnum():
            valor = secrets.token_hex(16)
            resp.set_cookie("avisador", valor, max_age=365 * 24 * 3600, path=url_for("inicio"),
                            httponly=True, samesite="Lax", secure=request.is_secure)
        return hashlib.sha256(valor.encode("utf-8")).hexdigest()

    @app.get("/avisar")
    def avisar():
        return pagina_avisar()

    @app.route("/avisar/<tabla>/<int:id>", methods=["GET", "POST"])
    def avisar_elemento(tabla, id):
        item = db.elemento_publico(tabla, id)
        if item is None:
            return pagina_avisar("Ese mensaje ya no está en la pantalla.", 404)
        if request.method == "GET":
            resp = Response(render_template("avisar_elemento.html", item=item, motivos=db.MOTIVOS_AVISO))
            huella_avisador(resp)
            return resp
        if not limite_avisos.permitir(request.remote_addr or "?"):
            return pagina_avisar("Se han enviado muchos avisos desde esta red. Espera unos minutos.", 429)
        motivo = request.form.get("motivo", "")
        if motivo not in db.MOTIVOS_AVISO:
            return render_template("avisar_elemento.html", item=item, motivos=db.MOTIVOS_AVISO,
                                   error_message="Elige un motivo."), 400
        resp = redirect(url_for("avisar", enviado=1), code=303)
        db.registrar_aviso(tabla, id, motivo, huella_avisador(resp))
        return resp

    return app


app = create_app()


if __name__ == "__main__":
    app.run()
