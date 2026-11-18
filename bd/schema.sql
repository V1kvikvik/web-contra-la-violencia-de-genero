-- Esquema de la base de datos SQLite del proyecto 25N.
-- Se aplica con init_db() en bd/db.py (o: sqlite3 datos/25n.db < bd/schema.sql).
-- Es idempotente: se puede ejecutar varias veces sin perder datos.

-- Mensajes cortos del mural de burbujas (T01, T02, T03, T07).
-- Se publican directamente si pasan el filtro automático (T03); si no, quedan
-- retenidos (visible = 0, retenido = 1) hasta que moderación decida.
-- Estados: visible = 1 → en pantalla · retenido = 1 → parado por el filtro ·
--          visible = 0 y retenido = 0 → retirado por moderación.
-- motivo:   por qué está retenido o retirado (solo lo ve moderación).
-- revisado: 1 si moderación lo publicó a mano; el filtro ya no lo vuelve a retirar.
-- (En una base de datos anterior, bd/db.py añade retenido, motivo y revisado al arrancar.)
CREATE TABLE IF NOT EXISTS mural (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    texto    TEXT    NOT NULL CHECK (length(trim(texto)) BETWEEN 1 AND 200),
    creado   TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%d %H:%M:%S', 'now')),
    visible  INTEGER NOT NULL DEFAULT 1 CHECK (visible IN (0, 1)),
    retenido INTEGER NOT NULL DEFAULT 0 CHECK (retenido IN (0, 1)),
    motivo   TEXT,
    revisado INTEGER NOT NULL DEFAULT 0 CHECK (revisado IN (0, 1))
);

-- Reflexiones del foro (T01, T02, T03, T09).
-- Por defecto esperan a que moderación las apruebe (ajuste foro_manual = 1): llegan
-- retenidas con el motivo «Pendiente de aprobación», o con el del filtro si lo activan.
-- Si el equipo desactiva foro_manual desde el panel, las que pasan el filtro se aprueban solas.
CREATE TABLE IF NOT EXISTS foro (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    titulo   TEXT    NOT NULL CHECK (length(trim(titulo)) BETWEEN 1 AND 80),
    texto    TEXT    NOT NULL CHECK (length(trim(texto))  BETWEEN 1 AND 1000),
    creado   TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%d %H:%M:%S', 'now')),
    aprobado INTEGER NOT NULL DEFAULT 0 CHECK (aprobado IN (0, 1)),
    retenido INTEGER NOT NULL DEFAULT 0 CHECK (retenido IN (0, 1)),
    motivo   TEXT,
    revisado INTEGER NOT NULL DEFAULT 0 CHECK (revisado IN (0, 1))
);

-- Índices para las consultas de la pantalla (/api/mural y /api/foro).
CREATE INDEX IF NOT EXISTS idx_mural_visible_creado ON mural (visible, creado DESC);
CREATE INDEX IF NOT EXISTS idx_foro_aprobado_creado ON foro (aprobado, creado DESC);

-- Palabras y expresiones del filtro automático (T03). Ver bd/filtro.py.
CREATE TABLE IF NOT EXISTS filtros (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    termino TEXT    NOT NULL UNIQUE,
    creado  TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%d %H:%M:%S', 'now'))
);

-- Ajustes de moderación que se cambian desde el panel (T03).
CREATE TABLE IF NOT EXISTS ajustes (
    clave TEXT PRIMARY KEY,
    valor TEXT NOT NULL
);
