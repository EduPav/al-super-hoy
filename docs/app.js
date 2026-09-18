/* Al super hoy - promociones de supermercados vigentes en Santa Fe capital.
 *
 * Todo el calculo vive en el navegador sobre el JSON que genera la ingesta.
 * Las preferencias (banco, monto habitual) quedan en localStorage: nunca salen
 * de esta maquina ni se publican con el sitio.
 */

const DIAS = ["L", "M", "X", "J", "V", "S", "D"];
const DIAS_LARGO = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"];

const pesos = new Intl.NumberFormat("es-AR", {
  style: "currency", currency: "ARS", maximumFractionDigits: 0,
});

const estado = {
  datos: null,
  vista: "hoy",
  prefs: leerPrefs(),
};

/* ---------- preferencias locales ---------- */

function leerPrefs() {
  const vacio = { gasto: null, bancos: [], ocultarSinConfirmar: false };
  try {
    return Object.assign(vacio, JSON.parse(localStorage.getItem("al-super-hoy") || "{}"));
  } catch (e) {
    return vacio;
  }
}

function guardarPrefs() {
  try {
    localStorage.setItem("al-super-hoy", JSON.stringify(estado.prefs));
  } catch (e) {
    /* Modo privado o almacenamiento bloqueado: la app funciona igual,
       solo que no recuerda las preferencias entre visitas. */
  }
}

/* ---------- calculo de ahorro ----------
 * El nucleo de la app. Un 20% con tope de $25.000 rinde 20% solo hasta los
 * $125.000; de ahi en mas el porcentaje efectivo se derrumba. Y una promo con
 * compra minima de $100.000 no sirve para una compra de $40.000.
 */

function ahorro(promo, gasto) {
  if (promo.tipo === "cuotas" || !promo.valor || !gasto) return 0;
  if (promo.compra_minima && gasto < promo.compra_minima) return 0;
  const bruto = gasto * (promo.valor / 100);
  return promo.tope ? Math.min(bruto, promo.tope) : bruto;
}

function porcentajeEfectivo(promo, gasto) {
  return gasto > 0 ? (ahorro(promo, gasto) / gasto) * 100 : 0;
}

/* ---------- utilidades ---------- */

const hoyIndice = () => (new Date().getDay() + 6) % 7;   // lunes = 0

function aplicaEnDia(promo, indice) {
  return promo.dias.includes(DIAS[indice]);
}

function vigente(promo) {
  const hoy = new Date().toISOString().slice(0, 10);
  if (promo.desde && hoy < promo.desde) return false;
  if (promo.hasta && hoy > promo.hasta) return false;
  return true;
}

function texto(valor) {
  const n = document.createElement("span");
  n.textContent = valor;
  return n.innerHTML;
}

function fechaCorta(iso) {
  if (!iso) return null;
  const [a, m, d] = iso.split("-");
  return `${d}/${m}/${a.slice(2)}`;
}

/* ---------- filtros ---------- */

function promosVisibles() {
  const { bancos, ocultarSinConfirmar } = estado.prefs;
  const sinConfirmar = new Set(estado.datos.revisar?.por_confirmar || []);
  return estado.datos.promos.filter((p) => {
    if (!vigente(p)) return false;
    if (ocultarSinConfirmar && sinConfirmar.has(p.comercio)) return false;
    if (bancos.length) {
      // Una promo sin bancos declarados aplica a varios, asi que no la escondemos.
      if (p.bancos.length && !p.bancos.some((b) => bancos.includes(b))) return false;
    }
    return true;
  });
}

function ordenar(promos, gasto) {
  return [...promos].sort((a, b) => {
    if (gasto) {
      const d = ahorro(b, gasto) - ahorro(a, gasto);
      if (d) return d;
    }
    return (b.valor || 0) - (a.valor || 0) || a.comercio.localeCompare(b.comercio);
  });
}

/* ---------- render de una promo ---------- */

function bloqueAhorro(promo, gasto) {
  if (!gasto) return "";
  if (promo.tipo === "cuotas") {
    return `<div class="ahorro"><strong>${promo.valor} cuotas sin interés</strong>
      <span class="detalle">No es un descuento: financia la compra.</span></div>`;
  }
  const falta = promo.compra_minima && gasto < promo.compra_minima
    ? promo.compra_minima - gasto : 0;
  if (falta) {
    return `<div class="ahorro nulo"><strong>No aplica</strong>
      <span class="detalle">Te faltan ${pesos.format(falta)} para llegar al mínimo
      de ${pesos.format(promo.compra_minima)}.</span></div>`;
  }
  const monto = ahorro(promo, gasto);
  if (!monto) return "";
  const efectivo = porcentajeEfectivo(promo, gasto);
  let detalle = `Pagás ${pesos.format(gasto - monto)} en vez de ${pesos.format(gasto)}.`;
  if (promo.tope && efectivo < promo.valor - 0.5) {
    detalle += ` Llegaste al tope: son ${efectivo.toFixed(1)}% reales, no ${promo.valor}%.`;
  } else if (promo.gasto_optimo && gasto < promo.gasto_optimo) {
    detalle += ` El tope te habilita hasta ${pesos.format(promo.gasto_optimo)}.`;
  }
  if (!promo.limites_conocidos) {
    // Sin tope publicado el calculo es un techo optimista, no una promesa.
    return `<div class="ahorro"><strong>Ahorrás hasta ${pesos.format(monto)}</strong>
      <span class="detalle">${detalle} La fuente no publica el tope ni el mínimo,
      así que puede haber un límite: confirmalo antes de la compra.</span></div>`;
  }
  return `<div class="ahorro"><strong>Ahorrás ${pesos.format(monto)}</strong>
    <span class="detalle">${detalle}</span></div>`;
}

function tarjetaPromo(promo, gasto) {
  const indice = hoyIndice();
  const dias = DIAS.map((d, i) =>
    `<span class="${promo.dias.includes(d) ? "on" : ""}" title="${DIAS_LARGO[i]}">${d}</span>`
  ).join("");

  // "Sin tope" solo se puede afirmar si alguna fuente publica los limites.
  // Si ninguna lo hace, decirlo: es la diferencia entre ahorrar y llevarse
  // una sorpresa en la caja.
  const tope = promo.tope
    ? pesos.format(promo.tope) + (promo.tope_periodo ? ` por ${promo.tope_periodo}` : "")
      + (promo.tope_por ? ` y por ${promo.tope_por}` : "")
    : (promo.limites_conocidos ? "Sin tope" : "No informado");
  const minimo = promo.compra_minima
    ? pesos.format(promo.compra_minima)
    : (promo.limites_conocidos ? "Sin mínimo" : "No informado");

  const datos = [
    [promo.tipo === "reintegro" ? "Tope de reintegro" : "Tope", tope],
    ["Compra mínima", minimo],
    ["Bancos", promo.bancos.length ? promo.bancos.join(", ") : "Varios bancos adheridos"],
    ["Modalidad", promo.modalidad.length ? promo.modalidad.join(" · ") : "—"],
  ].map(([k, v]) => `<div class="dato"><span class="k">${k}</span><span class="v">${texto(v)}</span></div>`)
   .join("");

  const vigencia = promo.hasta ? `Hasta el ${fechaCorta(promo.hasta)}` : "Sin fecha de fin informada";
  // Una promo puede venir de dos avisos de la misma fuente; mostramos la fuente
  // una sola vez para no repetir "MODO · MODO".
  const porNombre = new Map();
  promo.fuentes.forEach((f) => { if (!porNombre.has(f.nombre)) porNombre.set(f.nombre, f.url); });
  const enlaces = [...porNombre].map(([nombre, url]) =>
    `<a href="${url}" target="_blank" rel="noopener">${texto(nombre)}</a>`).join(" · ");

  const unidad = promo.tipo === "cuotas" ? "" : "%";
  return `<article class="promo">
    <div class="promo-encabezado">
      <h3 class="comercio">${texto(promo.comercio)}
        <span class="insignia ${promo.tipo}">${promo.tipo}</span></h3>
      <div class="valor">${promo.valor ?? "?"}${unidad}</div>
    </div>
    ${bloqueAhorro(promo, gasto)}
    <div class="datos">
      ${datos}
      <div class="dato"><span class="k">Días</span><div class="dias">${dias}</div></div>
    </div>
    <div class="promo-pie">
      <span>${vigencia}${aplicaEnDia(promo, indice) ? "" : " · no aplica hoy"}</span>
      <span>Fuente: ${enlaces}</span>
    </div>
  </article>`;
}

/* ---------- vistas ---------- */

function renderFiltros() {
  const cont = document.getElementById("filtros");
  const bancos = estado.datos.bancos || [];
  const chips = bancos.map((b) => {
    const activo = estado.prefs.bancos.includes(b);
    return `<button type="button" class="chip" data-banco="${texto(b)}"
      aria-pressed="${activo}">${texto(b)}</button>`;
  }).join("");

  cont.innerHTML = `<span class="etiqueta">Mis bancos:</span>${chips}
    <button type="button" class="chip" data-accion="confirmados"
      aria-pressed="${estado.prefs.ocultarSinConfirmar}">Solo comercios confirmados</button>`;

  cont.querySelectorAll("[data-banco]").forEach((b) => {
    b.addEventListener("click", () => {
      const nombre = b.dataset.banco;
      const i = estado.prefs.bancos.indexOf(nombre);
      if (i >= 0) estado.prefs.bancos.splice(i, 1);
      else estado.prefs.bancos.push(nombre);
      guardarPrefs();
      render();
    });
  });
  cont.querySelector('[data-accion="confirmados"]').addEventListener("click", () => {
    estado.prefs.ocultarSinConfirmar = !estado.prefs.ocultarSinConfirmar;
    guardarPrefs();
    render();
  });
}

function renderHoy() {
  const gasto = estado.prefs.gasto;
  const indice = hoyIndice();
  const deHoy = promosVisibles().filter((p) => aplicaEnDia(p, indice));
  const lista = document.getElementById("lista-hoy");

  if (!deHoy.length) {
    lista.innerHTML = `<p class="vacio">No hay promos para hoy con estos filtros.
      Probá en la pestaña <strong>Semana</strong>.</p>`;
    return;
  }
  lista.innerHTML = ordenar(deHoy, gasto).map((p) => tarjetaPromo(p, gasto)).join("");
}

function renderSemana() {
  const gasto = estado.prefs.gasto;
  const visibles = promosVisibles();
  const indice = hoyIndice();

  const bloques = DIAS.map((d, i) => {
    const delDia = ordenar(visibles.filter((p) => p.dias.includes(d)), gasto);
    if (!delDia.length) {
      return `<section class="dia-bloque ${i === indice ? "hoy" : ""}">
        <h3>${DIAS_LARGO[i]} <span class="cuenta">sin promos</span></h3></section>`;
    }
    const filas = delDia.slice(0, 8).map((p) => {
      const monto = ahorro(p, gasto);
      const der = gasto && monto
        ? `ahorrás ${pesos.format(monto)}`
        : (p.tope ? `tope ${pesos.format(p.tope)}` : "sin tope");
      const unidad = p.tipo === "cuotas" ? " cuotas" : "%";
      return `<div class="fila-compacta">
        <span><strong>${p.valor ?? "?"}${unidad}</strong> ${texto(p.comercio)}</span>
        <span class="der">${der}</span></div>`;
    }).join("");
    const resto = delDia.length > 8 ? `<div class="fila-compacta"><span class="der">
      y ${delDia.length - 8} más</span></div>` : "";
    return `<section class="dia-bloque ${i === indice ? "hoy" : ""}">
      <h3>${DIAS_LARGO[i]}${i === indice ? " · hoy" : ""}
        <span class="cuenta">${delDia.length} promos</span></h3>
      ${filas}${resto}</section>`;
  }).join("");

  document.getElementById("lista-semana").innerHTML = bloques;
}

function renderNovedades() {
  const n = estado.datos.novedades || {};
  const porId = new Map(estado.datos.promos.map((p) => [p.id, p]));
  const cont = document.getElementById("lista-novedades");
  const partes = [];

  if (n.comparado_con) {
    partes.push(`<p class="nota">Comparado con la corrida del
      ${new Date(n.comparado_con).toLocaleString("es-AR")}.</p>`);
  }

  const nuevas = (n.nuevas || []).map((id) => porId.get(id)).filter(Boolean);
  if (nuevas.length) {
    partes.push(`<h3>Nuevas (${nuevas.length})</h3><div class="lista">
      ${nuevas.map((p) => tarjetaPromo(p, estado.prefs.gasto)).join("")}</div>`);
  }

  if ((n.cambios || []).length) {
    partes.push(`<h3>Cambios</h3>` + n.cambios.map((c) =>
      `<div class="fila-compacta"><span>${texto(c.comercio)} — cambió el ${texto(c.campo)}</span>
       <span class="der">${texto(String(c.antes ?? "—"))} → ${texto(String(c.ahora ?? "—"))}</span></div>`
    ).join(""));
  }

  if ((n.terminadas || []).length) {
    partes.push(`<h3>Terminadas</h3>` + n.terminadas.map((t) =>
      `<div class="fila-compacta"><span>${texto(t.comercio)}</span>
       <span class="der">${texto(t.titulo || "")}</span></div>`).join(""));
  }

  cont.innerHTML = partes.length > 1 ? partes.join("")
    : `<p class="vacio">Sin cambios desde la última actualización.</p>`;
}

function renderFuentes() {
  const d = estado.datos;
  const filas = (d.fuentes || []).map((f) => `<tr>
    <td>${texto(f.nombre)}</td>
    <td class="${f.ok ? "estado-ok" : "estado-mal"}">${f.ok ? "OK" : "Falló"}</td>
    <td>${f.promos}</td>
    <td>${texto(f.error || "—")}</td></tr>`).join("");

  const porConfirmar = d.revisar?.por_confirmar || [];
  const desconocidos = d.revisar?.desconocidos || [];

  document.getElementById("lista-fuentes").innerHTML = `
    <p class="nota">Última actualización: ${new Date(d.generado).toLocaleString("es-AR")}.</p>
    <table class="fuentes">
      <thead><tr><th>Fuente</th><th>Estado</th><th>Promos</th><th>Detalle</th></tr></thead>
      <tbody>${filas}</tbody>
    </table>

    <details class="revisar" ${porConfirmar.length ? "open" : ""}>
      <summary>Comercios sin confirmar (${porConfirmar.length})</summary>
      <p class="nota">Aparecen en las promos y están en el registro, pero todavía no
        verificaste que tengan sucursal en la ciudad. Editá
        <code>datos/comercios-santa-fe.yml</code> para confirmarlos o sacarlos.</p>
      <ul>${porConfirmar.map((c) => `<li>${texto(c)}</li>`).join("")}</ul>
    </details>

    <details class="revisar">
      <summary>Comercios no reconocidos (${desconocidos.length})</summary>
      <p class="nota">Tienen promo vigente pero no están en el registro, así que la app
        los ignora. Si alguno está en Santa Fe, agregalo al registro.</p>
      <ul>${desconocidos.map((x) =>
        `<li>${texto(x.comercio)} — ${x.promos} promo(s)</li>`).join("")}</ul>
    </details>`;
}

/* ---------- orquestacion ---------- */

function renderFrescura() {
  const el = document.getElementById("frescura");
  const generado = new Date(estado.datos.generado);
  const horas = (Date.now() - generado.getTime()) / 36e5;
  const fallos = (estado.datos.fuentes || []).filter((f) => !f.ok);

  let clase = "frescura";
  let mensaje = `Actualizado ${generado.toLocaleDateString("es-AR")}`;
  if (horas > 72) {
    clase += " rota";
    mensaje = `Sin actualizar hace ${Math.floor(horas / 24)} días`;
  } else if (horas > 30) {
    clase += " vieja";
    mensaje = `Actualizado hace ${Math.floor(horas / 24)} día(s)`;
  }
  if (fallos.length) {
    clase += horas > 30 ? "" : " vieja";
    mensaje += ` · ${fallos.length} fuente(s) con error`;
  }
  el.className = clase;
  el.innerHTML = `<span class="punto"></span>${mensaje}`;
}

function render() {
  const total = promosVisibles().length;
  document.getElementById("subtitulo").textContent =
    `${total} promos vigentes en ${estado.datos.zona} · ` +
    new Date().toLocaleDateString("es-AR", { weekday: "long", day: "numeric", month: "long" });

  renderFrescura();
  renderFiltros();
  renderHoy();
  renderSemana();
  renderNovedades();
  renderFuentes();
}

function activarVista(vista) {
  estado.vista = vista;
  document.querySelectorAll("#pestanas button").forEach((b) =>
    b.classList.toggle("activa", b.dataset.vista === vista));
  document.querySelectorAll(".vista").forEach((s) =>
    s.hidden = s.id !== `vista-${vista}`);
}

function conectarControles() {
  const campo = document.getElementById("gasto");
  const limpiar = document.getElementById("limpiar-gasto");

  if (estado.prefs.gasto) campo.value = estado.prefs.gasto;
  limpiar.hidden = !estado.prefs.gasto;

  campo.addEventListener("input", () => {
    const valor = parseFloat(campo.value);
    estado.prefs.gasto = Number.isFinite(valor) && valor > 0 ? valor : null;
    limpiar.hidden = !estado.prefs.gasto;
    guardarPrefs();
    render();
  });
  limpiar.addEventListener("click", () => {
    campo.value = "";
    estado.prefs.gasto = null;
    limpiar.hidden = true;
    guardarPrefs();
    render();
  });

  document.getElementById("pestanas").addEventListener("click", (e) => {
    const boton = e.target.closest("button[data-vista]");
    if (boton) activarVista(boton.dataset.vista);
  });
}

async function iniciar() {
  try {
    const r = await fetch("datos/promos.json", { cache: "no-cache" });
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    estado.datos = await r.json();
  } catch (e) {
    document.getElementById("principal").innerHTML = `<div class="aviso error">
      <strong>No se pudieron cargar los datos.</strong><br>
      Si abriste el archivo con doble clic, el navegador bloquea la lectura del JSON.
      Levantá un servidor local con <code>python -m http.server</code> dentro de la
      carpeta <code>docs</code> y entrá a <code>http://localhost:8000</code>.
      <br><small>Detalle: ${texto(e.message)}</small></div>`;
    document.getElementById("subtitulo").textContent = "Error al cargar";
    return;
  }
  conectarControles();
  activarVista("hoy");
  render();
}

iniciar();
