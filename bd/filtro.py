"""T03 — Filtro automático de contenido (palabras y datos personales).

Funciones puras (sin Flask ni base de datos) para poder probarlas solas:

    filtro = Filtro(["puta", "maric*", "a fregar"], enlaces=True, correos=True,
                    telefonos=True, usuarios=True)
    filtro.motivo("Eres una p.u.t.a")   ->  'Palabra filtrada: «puta»'
    filtro.motivo("Ni una menos")       ->  None

Cómo se escribe un término del filtro:
    zorra        la palabra entera, con sus plurales (zorras) y escrita con trucos:
                 mayúsculas, tildes, letras repetidas (zorraaa), números por letras
                 (z0rra), separadores entre letras (z.o.r.r.a, z-o-r-r-a, z o r r a).
    maric*       cualquier palabra que empiece así (maricón, maricones, mariconazo...).
    a fregar     una expresión de varias palabras.
No hace falta escribir tildes: "maricon" ya cubre "maricón".
"""
import re
import unicodedata

# Sustituciones típicas para esquivar filtros (z0rra, put@, 5ubnormal...)
_LEET = str.maketrans({"0": "o", "1": "i", "3": "e", "4": "a", "5": "s", "7": "t",
                       "8": "b", "@": "a", "$": "s", "€": "e", "!": "i", "|": "i"})
# Caracteres que alguien puede meter entre las letras de una palabra: p.u.t.a, p-u-t-a, p*u*t*a
_SEP = r"[._\-*~+'\"`´·,:;/\\]{0,2}"
# Letras sueltas separadas por espacios: "p u t a" -> "puta"
_LETRAS_SUELTAS = re.compile(r"(?<![a-z0-9])(?:[a-z0-9] +){2,}[a-z0-9](?![a-z0-9])")

TERMINO_VALIDO = re.compile(r"^[a-zñáéíóúü]+(?: [a-zñáéíóúü]+)*\*?$")

_ENLACE = re.compile(r"https?://|www\.|\b[a-z0-9-]{2,}\.(?:com|es|net|org|io|ly|me|tv|gg|info|link|xyz|app|co)\b", re.I)
_CORREO = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
_TELEFONO = re.compile(r"(?<!\d)(?:\+?\d[\s.\-]?){9,}(?!\d)")
_USUARIO = re.compile(r"(?<![\w@])@[a-z0-9_.]{3,}", re.I)


def sin_tildes(texto):
    return "".join(c for c in unicodedata.normalize("NFKD", texto) if not unicodedata.combining(c))


def normalizar(texto):
    """Minúsculas, sin tildes, números de "leet" a letras y letras sueltas unidas."""
    t = sin_tildes(texto).lower().translate(_LEET)
    t = re.sub(r"\s+", " ", t)
    return _LETRAS_SUELTAS.sub(lambda m: m.group(0).replace(" ", ""), t)


def limpiar_termino(termino):
    """Forma en la que se guarda un término: minúsculas, sin tildes, espacios simples.
    Solo letras, espacios y un * final. Devuelve None si no es válido."""
    t = re.sub(r"\s+", " ", (termino or "").strip().lower())
    if not (2 <= len(t.rstrip("*")) <= 60) or not TERMINO_VALIDO.match(t):
        return None
    t = sin_tildes(t)
    if not re.match(r"^[a-z]+(?: [a-z]+)*\*?$", t):
        return None
    return t


def _patron_palabra(palabra):
    # cada letra puede repetirse (zorraaa) y llevar separadores entre medias (z.o.r.r.a)
    letras = [re.escape(c) + "+" for c in normalizar(palabra)]
    return _SEP.join(letras)


def _patron(termino):
    prefijo = termino.endswith("*")
    palabras = termino.rstrip("*").split(" ")
    cuerpo = r"\s+".join(_patron_palabra(p) for p in palabras)
    fin = r"[a-z0-9]*" if prefijo else r"(?:e?s)?(?![a-z0-9])"
    return r"(?<![a-z0-9])" + cuerpo + fin


class Filtro:
    def __init__(self, terminos=(), enlaces=True, correos=True, telefonos=True, usuarios=True):
        self.terminos = [t for t in terminos if t]
        self.reglas = {"enlaces": enlaces, "correos": correos, "telefonos": telefonos, "usuarios": usuarios}
        self._patrones = [(t, re.compile(_patron(t))) for t in self.terminos]

    def motivo(self, *textos):
        """Devuelve por qué el texto no puede publicarse, o None si puede."""
        original = "\n".join(t or "" for t in textos)
        if self.reglas["correos"] and _CORREO.search(original):
            return "Contiene un correo electrónico"
        if self.reglas["enlaces"] and _ENLACE.search(original):
            return "Contiene un enlace"
        if self.reglas["telefonos"] and _TELEFONO.search(original):
            return "Contiene un número de teléfono"
        if self.reglas["usuarios"] and _USUARIO.search(original):
            return "Contiene un @usuario de redes sociales"
        normal = normalizar(original)
        for termino, patron in self._patrones:
            if patron.search(normal):
                return "Palabra filtrada: «%s»" % termino
        return None
