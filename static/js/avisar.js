/* T03 — Páginas para avisar de un mensaje (templates/avisar.html y avisar_elemento.html).
 * Mejora progresiva: sin este archivo todo funciona igual.
 *  - /avisar: buscador que filtra la lista mientras se escribe (sin tildes ni mayúsculas).
 *  - Al enviar un aviso, el botón se desactiva para no mandarlo dos veces.
 */
(function () {
  'use strict';

  var norm = function (s) {
    return s.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase();
  };

  // ---------- Buscador de /avisar ----------
  var buscar = document.getElementById('buscar-avisar');
  if (buscar) {
    var items = Array.prototype.slice.call(document.querySelectorAll('.publicacion'));
    var sinResultados = document.getElementById('sin-resultados');
    buscar.addEventListener('input', function () {
      var q = norm(buscar.value.trim());
      var n = 0;
      items.forEach(function (li) {
        var ok = !q || norm(li.textContent).indexOf(q) !== -1;
        li.hidden = !ok;
        if (ok) n++;
      });
      sinResultados.hidden = n !== 0;
    });
  }

  // ---------- Evitar avisos dobles ----------
  var formulario = document.querySelector('form.formulario');
  if (formulario) {
    var boton = formulario.querySelector('button[type=submit]');
    var textoBoton = boton.textContent;
    formulario.addEventListener('submit', function (e) {
      if (boton.disabled) { e.preventDefault(); return; }
      boton.disabled = true;
      boton.textContent = 'Enviando…';
    });
    window.addEventListener('pageshow', function () {
      boton.disabled = false;
      boton.textContent = textoBoton;
    });
  }
})();
