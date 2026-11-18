/* T03 — Mejoras del panel de moderación (templates/admin.html).
 *
 * Mejora progresiva: sin este archivo todos los botones funcionan igual
 * (solo faltan los filtros, la búsqueda y la confirmación antes de borrar).
 *
 *  - Hora de la última carga y aviso de la última acción (se cierra solo).
 *  - Cada 30 s pregunta a /admin/estado si hay elementos pendientes nuevos y lo indica
 *    sin recargar (así no se pierde lo que se esté escribiendo).
 *  - Filtro (Todo / Mural / Foro / Retirado) y búsqueda en las publicaciones y en el filtro.
 *  - «Ver texto completo» en reflexiones largas.
 *  - Confirmación antes de borrar y bloqueo de dobles envíos.
 *
 * La URL de /admin/estado llega en <body data-api-estado="…"> (nunca rutas escritas a mano).
 * Texto de usuario siempre con textContent.
 */
(function () {
  'use strict';

  var norm = function (s) {
    return s.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase();
  };
  var ahora = function () {
    return new Date().toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' });
  };

  // ---------- Hora de la última carga ----------
  var hora = document.getElementById('adm-hora');
  if (hora) {
    hora.textContent = 'Actualizado a las ' + ahora();
    hora.hidden = false;
  }

  // Quita ?hecho=… de la dirección para que recargar no repita el aviso
  if (location.search && history.replaceState) {
    history.replaceState(null, '', location.pathname + location.hash);
  }

  // ---------- Aviso de la última acción: se cierra solo a los 8 s, o con la × ----------
  var aviso = document.getElementById('adm-aviso');
  if (aviso) {
    var cerrarAviso = function () {
      aviso.classList.add('adm-saliendo');
      setTimeout(function () { aviso.hidden = true; }, 400);
    };
    var x = document.createElement('button');
    x.type = 'button';
    x.className = 'adm-aviso-cerrar';
    x.setAttribute('aria-label', 'Cerrar aviso');
    x.textContent = '×';
    x.addEventListener('click', cerrarAviso);
    aviso.appendChild(x);
    setTimeout(cerrarAviso, 8000);
  }

  // ---------- Novedades mientras el panel está abierto ----------
  var urlEstado = document.body.dataset.apiEstado;
  var inicial = Number(document.body.dataset.retenidos) || 0;
  var novedades = document.getElementById('adm-novedades');
  var comprobar = function () {
    fetch(urlEstado, { cache: 'no-store', credentials: 'same-origin' })
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (d) {
        if (!d || !(d.retenidos > inicial)) return;
        document.getElementById('adm-novedades-texto').textContent =
          'Novedades (' + ahora() + '): ' + d.retenidos +
          (d.retenidos === 1 ? ' pendiente' : ' pendientes') + ' de revisar.';
        novedades.hidden = false;
        document.title = '(' + d.retenidos + ') Moderación · 25N';
      })
      .catch(function () {});
  };
  if (urlEstado && novedades) {
    setInterval(comprobar, Number(window.ADMIN_SONDEO_MS) || 30000);
  }

  // ---------- Filtro y búsqueda de publicaciones ----------
  var lista = document.getElementById('lista-pub');
  if (lista) {
    var filtro = 'todo';
    var busqueda = '';
    var filas = Array.prototype.slice.call(lista.querySelectorAll('.adm-fila'));
    var sinResultados = lista.querySelector('.adm-sin-resultados');
    var botones = document.querySelectorAll('[data-filtro]');
    var aplicar = function () {
      var n = 0;
      filas.forEach(function (f) {
        var ok = (filtro === 'todo' || f.dataset.tipo === filtro || f.dataset.estado === filtro) &&
                 (!busqueda || norm(f.querySelector('.adm-fila-cuerpo').textContent).indexOf(busqueda) !== -1);
        f.hidden = !ok;
        if (ok) n++;
      });
      sinResultados.hidden = n !== 0;
    };
    botones.forEach(function (b) {
      b.addEventListener('click', function () {
        filtro = b.dataset.filtro;
        botones.forEach(function (o) { o.setAttribute('aria-pressed', o === b ? 'true' : 'false'); });
        aplicar();
      });
    });
    var buscar = document.getElementById('buscar-pub');
    buscar.addEventListener('input', function () {
      busqueda = norm(buscar.value.trim());
      aplicar();
    });
    document.getElementById('herramientas-pub').hidden = false;
  }

  // ---------- Búsqueda dentro del filtro de palabras ----------
  var buscarFiltro = document.getElementById('buscar-filtro');
  if (buscarFiltro) {
    buscarFiltro.closest('label').hidden = false;
    var chips = Array.prototype.slice.call(document.querySelectorAll('#lista-filtro .adm-chip'));
    buscarFiltro.addEventListener('input', function () {
      var q = norm(buscarFiltro.value.trim());
      chips.forEach(function (c) { c.hidden = !!q && norm(c.textContent).indexOf(q) === -1; });
    });
  }

  // ---------- «Ver texto completo» en reflexiones largas ----------
  document.querySelectorAll('.adm-recortado').forEach(function (p) {
    if (p.scrollHeight <= p.clientHeight + 2) return;
    var b = document.createElement('button');
    b.type = 'button';
    b.className = 'adm-ver-mas';
    b.textContent = 'Ver texto completo';
    b.setAttribute('aria-expanded', 'false');
    b.addEventListener('click', function () {
      var abrir = b.getAttribute('aria-expanded') === 'false';
      p.classList.toggle('adm-recortado', !abrir);
      b.setAttribute('aria-expanded', String(abrir));
      b.textContent = abrir ? 'Ver menos' : 'Ver texto completo';
    });
    p.parentNode.insertBefore(b, p.nextSibling);
  });

  // ---------- Confirmación al borrar y bloqueo de dobles envíos ----------
  var dialogo = document.getElementById('adm-confirmar');
  var enEspera = null;
  var enviar = function (f) {
    f.setAttribute('data-confirmado', '1');
    if (f.requestSubmit) f.requestSubmit(); else f.submit();
  };
  document.querySelectorAll('main form').forEach(function (f) {
    f.addEventListener('submit', function (e) {
      var b = f.querySelector('button[type=submit]');
      if (b.disabled) { e.preventDefault(); return; }
      var pregunta = f.getAttribute('data-confirmar');
      if (pregunta && f.getAttribute('data-confirmado') !== '1') {
        e.preventDefault();
        var fila = f.closest('.adm-fila');
        var cita = fila.querySelector('.adm-titulo') || fila.querySelector('.adm-texto');
        if (dialogo && typeof dialogo.showModal === 'function') {
          enEspera = f;
          document.getElementById('adm-confirmar-titulo').textContent = pregunta;
          document.getElementById('adm-confirmar-cita').textContent = cita.textContent;
          dialogo.returnValue = '';
          dialogo.showModal();
        } else if (window.confirm(pregunta + ' Esta acción no se puede deshacer.')) {
          enviar(f);
        }
        return;
      }
      b.disabled = true;
    });
  });
  if (dialogo) {
    dialogo.addEventListener('close', function () {
      var f = enEspera;
      enEspera = null;
      if (f && dialogo.returnValue === 'si') enviar(f);
    });
  }
  // Al volver con «Atrás» el navegador puede restaurar la página con los botones desactivados
  window.addEventListener('pageshow', function () {
    document.querySelectorAll('main form').forEach(function (f) {
      f.removeAttribute('data-confirmado');
      var b = f.querySelector('button[type=submit]');
      if (b) b.disabled = false;
    });
  });
})();
