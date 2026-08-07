/* AnoniPRO — lógica de la interfaz.
 * Todo el procesamiento ocurre en el servidor local; este archivo solo
 * pinta la vista previa, gestiona los interruptores y la verificación.
 */

"use strict";

pdfjsLib.GlobalWorkerOptions.workerSrc = "vendor/pdfjs/pdf.worker.min.js";

// ───────────────────────── estado global ─────────────────────────
const estado = {
  categorias: [],            // catálogo del servidor
  activas: new Set(),        // ids de categorías activas
  doc: null,                 // respuesta de /api/documentos
  detecciones: new Map(),    // id → {…deteccion, aprobada}
  zonasManuales: [],         // [{pagina,x0,y0,x1,y1, elemento}]
  textosManuales: [],        // ["texto", …]
  escalas: new Map(),        // nº de página → escala de render
  modoDibujo: false,
  clicTrasArrastre: false,   // suprime el clic que remata un arrastre de zona
  cola: [],                  // archivos pendientes (proceso por lotes simple)
  ajustesSucios: false,
};

const $ = (id) => document.getElementById(id);

// Datos de identidad y contacto: el mínimo común a casi todos los perfiles.
const BASE_IDENTIDAD = ["persona", "dni_nie", "pasaporte", "fecha_nacimiento",
  "direccion", "telefono", "email", "localidad", "personalizada"];

// Perfiles predefinidos: qué categorías se activan en cada tipo de trabajo.
// (null = todas). El usuario puede crear los suyos y se guardan en el navegador.
const PERFILES_BASE = {
  "Todo activado": null,

  "Documento clínico": [...BASE_IDENTIDAD, "cip", "nhc", "nuss", "iban", "tarjeta"],

  "Publicación científica": [...BASE_IDENTIDAD, "cip", "nhc", "nuss", "centro",
    "servicio_unidad", "sanitario", "colegiado", "organizacion", "logo", "fecha",
    "iban", "tarjeta"],

  "Docencia": [...BASE_IDENTIDAD, "cip", "nhc", "nuss", "centro", "sanitario",
    "colegiado", "organizacion", "logo", "fecha", "iban", "tarjeta"],

  "Jurídico (contratos y escritos)": [...BASE_IDENTIDAD, "iban", "tarjeta", "cif",
    "expediente", "catastro", "matricula", "organizacion", "logo", "fecha"],

  "Empresa y RR. HH.": [...BASE_IDENTIDAD, "iban", "tarjeta", "cif", "nuss",
    "expediente", "matricula", "organizacion", "logo"],

  "Facturas y contabilidad": [...BASE_IDENTIDAD, "iban", "tarjeta", "cif",
    "expediente", "organizacion", "logo"],

  "Documento personal": [...BASE_IDENTIDAD, "iban", "tarjeta", "nuss",
    "matricula", "catastro", "expediente"],
};

// ───────────────────────── arranque ─────────────────────────
async function iniciar() {
  aplicarTemaGuardado();

  const info = await (await fetch("/api/estado")).json();
  $("version-app").textContent = "AnoniPRO " + info.version;
  $("ttl-minutos").textContent = info.ttl_minutos;
  $("estado-modelo").textContent = "Detector: " + info.modelo_ner;
  const chipOcr = $("estado-ocr");
  if (info.ocr_disponible) {
    chipOcr.textContent = "OCR: " + (info.ocr_espanol ? "español ✓" : "sin español");
    chipOcr.title = "Reconocimiento de escaneados e imágenes disponible";
  } else {
    chipOcr.textContent = "OCR: no instalado";
    chipOcr.title = "No se podrán procesar escaneados ni imágenes en este equipo";
  }

  if (info.requiere_password && !info.autenticado) {
    $("pantalla-login").classList.remove("oculto");
    $("form-login").addEventListener("submit", enviarLogin);
    return;
  }
  await arrancarAplicacion();
}

async function enviarLogin(ev) {
  ev.preventDefault();
  const r = await fetch("/api/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ password: $("campo-password").value }),
  });
  if (r.ok) {
    $("pantalla-login").classList.add("oculto");
    await arrancarAplicacion();
  } else {
    $("error-login").classList.remove("oculto");
  }
}

async function arrancarAplicacion() {
  $("aplicacion").classList.remove("oculto");
  estado.categorias = await (await fetch("/api/categorias")).json();
  estado.categorias
    .filter((c) => c.activa_por_defecto)
    .forEach((c) => estado.activas.add(c.id));
  pintarInterruptores();
  pintarSelectorPerfiles();
  // El desplegable debe reflejar el estado real de los interruptores al arrancar
  sincronizarPerfilConInterruptores();
  inicializarEditoresTerminos();
  conectarEventos();
  // Refleja en el panel si la capa 3 quedó activada de una sesión anterior
  fetch("/api/capa3/estado").then((r) => r.json()).then((e) => actualizarEstadoCapa3(e.config)).catch(() => {});
}

// ───────────────────────── panel de interruptores ─────────────────────────
function pintarInterruptores() {
  const cont = $("lista-categorias");
  cont.innerHTML = "";
  // Los grupos y su orden los define el servidor (catálogo de categorías),
  // así que añadir una categoría nueva no obliga a tocar la interfaz.
  const grupos = [...new Set(estado.categorias
    .slice()
    .sort((a, b) => (a.orden_grupo ?? 99) - (b.orden_grupo ?? 99))
    .map((c) => c.grupo))];
  for (const grupo of grupos) {
    const cats = estado.categorias.filter((c) => c.grupo === grupo);
    if (!cats.length) continue;
    const div = document.createElement("div");
    div.className = "grupo-categorias";
    div.innerHTML = `<div class="titulo-grupo">${escapaHtml(cats[0].grupo_nombre || grupo)}</div>`;
    for (const c of cats) {
      const fila = document.createElement("label");
      fila.className = "interruptor";
      fila.title = c.descripcion;
      fila.innerHTML = `
        <input type="checkbox" data-categoria="${c.id}" ${estado.activas.has(c.id) ? "checked" : ""}>
        <span class="punto-color" style="background:${c.color}"></span>
        <span>${c.nombre}</span>`;
      fila.querySelector("input").addEventListener("change", (ev) => {
        ev.target.checked ? estado.activas.add(c.id) : estado.activas.delete(c.id);
        sincronizarPerfilConInterruptores();
        marcarAjustesSucios();
      });
      div.appendChild(fila);
    }
    cont.appendChild(div);
  }
}

function marcarAjustesSucios() {
  estado.ajustesSucios = true;
  if (estado.doc) $("boton-reanalizar").classList.remove("oculto");
}

// ───────────────────────── perfiles ─────────────────────────
function perfilesGuardados() {
  try { return JSON.parse(localStorage.getItem("anonipro_perfiles") || "{}"); }
  catch { return {}; }
}

function pintarSelectorPerfiles() {
  const sel = $("selector-perfil");
  sel.innerHTML = "";
  const todos = { ...PERFILES_BASE, ...perfilesGuardados() };
  for (const nombre of Object.keys(todos)) {
    const op = document.createElement("option");
    op.value = nombre;
    op.textContent = nombre;
    sel.appendChild(op);
  }
}

function aplicarPerfil(nombre) {
  const todos = { ...PERFILES_BASE, ...perfilesGuardados() };
  const ids = todos[nombre];
  if (ids === undefined) return;              // «ajustes propios»: no cambia nada
  estado.activas = new Set(ids === null ? estado.categorias.map((c) => c.id) : ids);
  pintarInterruptores();
  marcarAjustesSucios();
}

const OPCION_PROPIA = "— ajustes propios —";

/** Interruptores activos de un perfil (null = todas las categorías). */
function categoriasDelPerfil(nombre) {
  const todos = { ...PERFILES_BASE, ...perfilesGuardados() };
  const ids = todos[nombre];
  if (ids === undefined) return null;
  return new Set(ids === null ? estado.categorias.map((c) => c.id) : ids);
}

/** Mantiene el desplegable diciendo la verdad: si tocas los interruptores a mano
 *  y ya no coinciden con ningún perfil, se muestra «ajustes propios». */
function sincronizarPerfilConInterruptores() {
  const sel = $("selector-perfil");
  const iguales = (a, b) => a && b && a.size === b.size && [...a].every((x) => b.has(x));

  const nombres = Object.keys({ ...PERFILES_BASE, ...perfilesGuardados() });
  const coincide = nombres.find((n) => iguales(categoriasDelPerfil(n), estado.activas));

  const propia = [...sel.options].find((o) => o.value === OPCION_PROPIA);
  if (coincide) {
    if (propia) propia.remove();
    sel.value = coincide;
  } else {
    if (!propia) {
      const op = document.createElement("option");
      op.value = op.textContent = OPCION_PROPIA;
      sel.appendChild(op);
    }
    sel.value = OPCION_PROPIA;
  }
}

function guardarPerfilActual() {
  const nombre = prompt("Nombre del perfil (la configuración actual de interruptores):");
  if (!nombre) return;
  const guardados = perfilesGuardados();
  guardados[nombre] = [...estado.activas];
  localStorage.setItem("anonipro_perfiles", JSON.stringify(guardados));
  pintarSelectorPerfiles();
  $("selector-perfil").value = nombre;
}

// ───────── editor de términos por casillas individuales ─────────
// Cada término va en su propia casilla. Más claro para el usuario que una
// caja de varias líneas. Se usa para «redactar siempre» y «no redactar nunca».
function anadirCasilla(idContenedor, valor = "") {
  const cont = $(idContenedor);
  const fila = document.createElement("div");
  fila.className = "fila-termino";
  const input = document.createElement("input");
  input.type = "text";
  input.className = "casilla-termino";
  input.placeholder = "Escribe un término…";
  input.value = valor;
  input.addEventListener("input", marcarAjustesSucios);
  const quitar = document.createElement("button");
  quitar.className = "boton-quitar-termino";
  quitar.textContent = "✕";
  quitar.title = "Quitar esta casilla";
  quitar.addEventListener("click", () => {
    fila.remove();
    if (!cont.querySelector(".fila-termino")) anadirCasilla(idContenedor); // deja siempre una
    marcarAjustesSucios();
  });
  fila.append(input, quitar);
  cont.appendChild(fila);
  return input;
}

function inicializarEditoresTerminos() {
  // Arranca con 3 casillas para «redactar siempre» y 2 para «no redactar nunca».
  for (let i = 0; i < 3; i++) anadirCasilla("lista-negra");
  for (let i = 0; i < 2; i++) anadirCasilla("lista-blanca");
}

function terminosDe(idContenedor) {
  return [...$(idContenedor).querySelectorAll(".casilla-termino")]
    .map((i) => i.value.trim())
    .filter(Boolean);
}

// ───────────────────────── subida y análisis ─────────────────────────

async function subirArchivo(archivo) {
  const esImagenOEscaneo = /\.(pdf|jpe?g|png|tiff?|bmp|webp)$/i.test(archivo.name);
  mostrarProgreso(
    `Analizando «${archivo.name}»…` +
    (estado.cola.length ? ` (${estado.cola.length} en cola)` : "") +
    (esImagenOEscaneo ? "\nSi está escaneado, el OCR puede tardar en documentos largos." : ""));
  const datos = new FormData();
  datos.append("archivo", archivo);
  datos.append("categorias", JSON.stringify([...estado.activas]));
  datos.append("lista_personalizada", JSON.stringify(terminosDe("lista-negra")));
  datos.append("lista_blanca", JSON.stringify(terminosDe("lista-blanca")));

  const r = await fetch("/api/documentos", { method: "POST", body: datos });
  if (!r.ok) {
    const err = await r.json().catch(() => ({ detail: "Error desconocido." }));
    ocultarProgreso();
    alert("No se pudo procesar el documento:\n\n" + err.detail);
    procesarSiguienteDeCola();
    return;
  }
  estado.doc = await r.json();
  cargarDetecciones(estado.doc.detecciones);
  estado.zonasManuales = [];
  estado.textosManuales = [];
  $("nombre-documento").textContent = estado.doc.nombre +
    (estado.cola.length ? `  ·  quedan ${estado.cola.length} en cola` : "");
  $("boton-zona-manual").classList.toggle("oculto", estado.doc.tipo !== "pdf");

  // Banner OCR: avisar de que el texto se leyó por reconocimiento óptico
  const banner = $("banner-ocr");
  let avisos = [];
  if (estado.doc.por_ocr) {
    avisos.push("🔎 <strong>Documento leído con OCR.</strong> " +
      (estado.doc.aviso_ocr || "") +
      " Revisa con atención: el OCR puede equivocarse o no leer algún dato " +
      "(sobre todo correos y símbolos). Puedes marcar zonas a mano si hace falta.");
  }
  if (estado.doc.capa3_no_disponible) {
    avisos.push("⚠️ <strong>La IA local (capa 3) está activada pero no respondió.</strong> " +
      "Se ha analizado solo con las capas 1-2. Revisa el servidor en «⚙️ Ajustes de IA».");
  }
  if (avisos.length) {
    banner.innerHTML = avisos.join("<br><br>");
    banner.classList.remove("oculto");
  } else {
    banner.classList.add("oculto");
  }

  ocultarProgreso();
  $("area-documento").classList.remove("oculto");
  $("panel-detecciones").classList.remove("oculto");
  $("zona-soltar").classList.add("oculto");

  if (estado.doc.tipo === "pdf") await pintarPdf();
  else pintarDocx();
  pintarListaDetecciones();
}

function cargarDetecciones(lista) {
  estado.detecciones = new Map();
  for (const d of lista) estado.detecciones.set(d.id, { ...d, aprobada: true });
}

async function reanalizar() {
  if (!estado.doc) return;
  mostrarProgreso("Volviendo a analizar…");
  const r = await fetch(`/api/documentos/${estado.doc.id}/analizar`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      categorias: [...estado.activas],
      lista_personalizada: terminosDe("lista-negra"),
      lista_blanca: terminosDe("lista-blanca"),
    }),
  });
  ocultarProgreso();
  $("area-documento").classList.remove("oculto");
  if (!r.ok) {
    if (r.status === 404) { alert("El documento caducó en memoria. Vuelve a subirlo."); cerrarDocumento(false); }
    return;
  }
  const datos = await r.json();
  cargarDetecciones(datos.detecciones);
  estado.ajustesSucios = false;
  $("boton-reanalizar").classList.add("oculto");
  if (estado.doc.tipo === "pdf") pintarResaltadosPdf();
  else pintarDocx();
  pintarListaDetecciones();
}

// ───────────────────────── vista previa PDF ─────────────────────────
async function pintarPdf() {
  const cont = $("contenedor-paginas");
  cont.innerHTML = "";
  const bytes = await (await fetch(`/api/documentos/${estado.doc.id}/original`)).arrayBuffer();
  const pdf = await pdfjsLib.getDocument({ data: bytes }).promise;

  // Ancho útil de la zona central (con margen), acotado a un rango razonable
  const anchoZona = $("zona-central").clientWidth || 840;
  const anchoDisponible = Math.min(Math.max(anchoZona - 60, 400), 860);
  for (let n = 1; n <= pdf.numPages; n++) {
    const pagina = await pdf.getPage(n);
    const vista1 = pagina.getViewport({ scale: 1 });
    const escala = anchoDisponible / vista1.width;
    estado.escalas.set(n - 1, escala);
    const vista = pagina.getViewport({ scale: escala });

    const marco = document.createElement("div");
    marco.className = "pagina-pdf";
    marco.dataset.pagina = n - 1;
    marco.style.width = vista.width + "px";
    marco.style.height = vista.height + "px";

    const lienzo = document.createElement("canvas");
    const proporcion = window.devicePixelRatio || 1;
    lienzo.width = vista.width * proporcion;
    lienzo.height = vista.height * proporcion;
    lienzo.style.width = vista.width + "px";
    lienzo.style.height = vista.height + "px";

    const capa = document.createElement("div");
    capa.className = "capa-resaltados";
    capa.dataset.pagina = n - 1;
    conectarDibujoManual(capa, n - 1);

    marco.appendChild(lienzo);
    marco.appendChild(capa);
    cont.appendChild(marco);

    await pagina.render({
      canvasContext: lienzo.getContext("2d"),
      viewport: pagina.getViewport({ scale: escala * proporcion }),
    }).promise;
  }
  pintarResaltadosPdf();
}

function colorDeCategoria(id) {
  const c = estado.categorias.find((x) => x.id === id);
  return c ? c.color : "#888";
}

function pintarResaltadosPdf() {
  document.querySelectorAll(".resaltado").forEach((e) => e.remove());
  for (const [id, d] of estado.detecciones) {
    const capa = document.querySelector(`.capa-resaltados[data-pagina="${d.pagina}"]`);
    if (!capa) continue;
    const escala = estado.escalas.get(d.pagina) || 1;
    for (const [x0, y0, x1, y1] of d.rects) {
      const caja = document.createElement("div");
      caja.className = "resaltado" + (d.aprobada ? "" : " descartado");
      caja.dataset.deteccion = id;
      caja.style.left = x0 * escala + "px";
      caja.style.top = y0 * escala + "px";
      caja.style.width = (x1 - x0) * escala + "px";
      caja.style.height = (y1 - y0) * escala + "px";
      caja.style.background = colorDeCategoria(d.categoria);
      caja.title = `${d.texto} (clic para incluir/excluir)`;
      caja.addEventListener("click", (ev) => {
        ev.stopPropagation();
        // En modo dibujo, un clic simple sigue alternando la detección;
        // solo se ignora el clic que remata un ARRASTRE (fin de dibujar zona).
        if (estado.clicTrasArrastre) return;
        alternarDeteccion(id);
        localizarFilaPanel(id);
      });
      capa.appendChild(caja);
    }
  }
}

// Dibujo de zonas manuales sobre el PDF
function conectarDibujoManual(capa, numPagina) {
  let inicio = null, caja = null;
  capa.addEventListener("mousedown", (ev) => {
    if (!estado.modoDibujo || ev.button !== 0) return;
    const marco = capa.getBoundingClientRect();
    inicio = { x: ev.clientX - marco.left, y: ev.clientY - marco.top };
    caja = document.createElement("div");
    caja.className = "rect-en-curso";
    capa.appendChild(caja);
    ev.preventDefault();
  });
  capa.addEventListener("mousemove", (ev) => {
    if (!inicio || !caja) return;
    const marco = capa.getBoundingClientRect();
    const x = ev.clientX - marco.left, y = ev.clientY - marco.top;
    caja.style.left = Math.min(x, inicio.x) + "px";
    caja.style.top = Math.min(y, inicio.y) + "px";
    caja.style.width = Math.abs(x - inicio.x) + "px";
    caja.style.height = Math.abs(y - inicio.y) + "px";
  });
  const terminar = (ev) => {
    if (!inicio || !caja) return;
    const marco = capa.getBoundingClientRect();
    const x = ev.clientX - marco.left, y = ev.clientY - marco.top;
    const escala = estado.escalas.get(numPagina) || 1;
    const zona = {
      pagina: numPagina,
      x0: Math.min(x, inicio.x) / escala, y0: Math.min(y, inicio.y) / escala,
      x1: Math.max(x, inicio.x) / escala, y1: Math.max(y, inicio.y) / escala,
    };
    caja.remove();
    inicio = null; caja = null;
    if ((zona.x1 - zona.x0) > 3 && (zona.y1 - zona.y0) > 3) {
      anadirZonaManual(zona, capa, escala);
      // El clic que remata este arrastre no debe alternar el resaltado de
      // debajo. El evento click llega justo después del mouseup; la marca se
      // limpia sola en cuanto pasa (timeout 0), así nunca se queda pegada.
      estado.clicTrasArrastre = true;
      setTimeout(() => { estado.clicTrasArrastre = false; }, 0);
    }
  };
  capa.addEventListener("mouseup", terminar);
  capa.addEventListener("mouseleave", (ev) => { if (inicio) terminar(ev); });
}

function anadirZonaManual(zona, capa, escala) {
  const caja = document.createElement("div");
  caja.className = "resaltado-manual";
  caja.style.left = zona.x0 * escala + "px";
  caja.style.top = zona.y0 * escala + "px";
  caja.style.width = (zona.x1 - zona.x0) * escala + "px";
  caja.style.height = (zona.y1 - zona.y0) * escala + "px";
  caja.title = "Zona manual (clic para quitarla)";
  caja.addEventListener("click", (ev) => {
    ev.stopPropagation();
    if (estado.clicTrasArrastre) return;  // no quitar la zona recién dibujada
    estado.zonasManuales = estado.zonasManuales.filter((z) => z.elemento !== caja);
    caja.remove();
    pintarListaDetecciones();
  });
  capa.appendChild(caja);
  zona.elemento = caja;
  estado.zonasManuales.push(zona);
  pintarListaDetecciones();
}

// ───────────────────────── vista previa DOCX ─────────────────────────
function pintarDocx() {
  const cont = $("contenedor-paginas");
  cont.innerHTML = "";
  const hoja = document.createElement("div");
  hoja.className = "bloque-docx";

  // detecciones agrupadas por bloque, ordenadas por posición
  const porBloque = new Map();
  for (const [id, d] of estado.detecciones) {
    if (!porBloque.has(d.bloque)) porBloque.set(d.bloque, []);
    porBloque.get(d.bloque).push({ id, ...d });
  }

  for (const b of estado.doc.bloques) {
    const p = document.createElement("p");
    if (b.origen !== "cuerpo") p.className = "origen-" + b.origen;
    const dets = (porBloque.get(b.indice) || []).sort((a, z) => a.inicio - z.inicio);
    let cursor = 0;
    for (const d of dets) {
      if (d.inicio < cursor) continue; // solapada, ya cubierta
      p.appendChild(document.createTextNode(b.texto.slice(cursor, d.inicio)));
      const marca = document.createElement("mark");
      marca.className = "resaltado-texto" + (estado.detecciones.get(d.id).aprobada ? "" : " descartado");
      marca.dataset.deteccion = d.id;
      marca.textContent = b.texto.slice(d.inicio, d.fin);
      marca.style.background = colorDeCategoria(d.categoria) + "66";
      marca.title = "Clic para incluir/excluir";
      marca.addEventListener("click", () => {
        alternarDeteccion(d.id);
        localizarFilaPanel(d.id);
      });
      p.appendChild(marca);
      cursor = d.fin;
    }
    p.appendChild(document.createTextNode(b.texto.slice(cursor)));
    if (!b.texto.trim()) p.innerHTML = "&nbsp;";
    hoja.appendChild(p);
  }
  cont.appendChild(hoja);
}

// ───────────────────────── lista de detecciones ─────────────────────────
function alternarDeteccion(id, valor) {
  const d = estado.detecciones.get(id);
  if (!d) return;
  d.aprobada = valor !== undefined ? valor : !d.aprobada;
  // sincroniza resaltados y fila de lista
  document.querySelectorAll(`[data-deteccion="${id}"]`).forEach((e) => {
    if (e.classList.contains("fila-deteccion")) {
      e.classList.toggle("descartada", !d.aprobada);
      e.querySelector("input").checked = d.aprobada;
    } else {
      e.classList.toggle("descartado", !d.aprobada);
    }
  });
  actualizarContador();
}

function actualizarContador() {
  const aprobadas = [...estado.detecciones.values()].filter((d) => d.aprobada).length;
  $("contador-detecciones").textContent =
    `${aprobadas + estado.zonasManuales.length + estado.textosManuales.length}`;
}

function pintarListaDetecciones() {
  const cont = $("lista-detecciones");
  cont.innerHTML = "";

  // extras manuales primero
  if (estado.textosManuales.length || estado.zonasManuales.length) {
    const t = document.createElement("div");
    t.className = "grupo-detecciones-titulo";
    t.textContent = "Añadidos a mano";
    cont.appendChild(t);
    estado.textosManuales.forEach((texto, i) => {
      const fila = document.createElement("div");
      fila.className = "fila-deteccion";
      fila.innerHTML = `<input type="checkbox" checked disabled>
        <div class="cuerpo-deteccion"><div class="texto-deteccion">${escapaHtml(texto)}</div>
        <div class="metadatos-deteccion"><span class="etiqueta-capa">texto manual</span></div></div>
        <button class="boton-enlace" title="Quitar">✖</button>`;
      fila.querySelector("button").addEventListener("click", () => {
        estado.textosManuales.splice(i, 1);
        pintarListaDetecciones();
      });
      cont.appendChild(fila);
    });
    if (estado.zonasManuales.length) {
      const fila = document.createElement("div");
      fila.className = "fila-deteccion";
      fila.innerHTML = `<input type="checkbox" checked disabled>
        <div class="cuerpo-deteccion"><div class="texto-deteccion">${estado.zonasManuales.length} zona(s) dibujada(s)</div>
        <div class="metadatos-deteccion"><span class="etiqueta-capa">zona manual</span></div>
        <div class="contexto-deteccion">Clic sobre la zona negra del documento para quitarla.</div></div>`;
      cont.appendChild(fila);
    }
  }

  // detecciones automáticas agrupadas por página/bloque de aparición
  const ordenadas = [...estado.detecciones.values()]
    .sort((a, z) => (a.pagina ?? a.bloque ?? 0) - (z.pagina ?? z.bloque ?? 0) || a.inicio - z.inicio);

  let grupoActual = null;
  for (const d of ordenadas) {
    if (estado.doc.tipo === "pdf" && d.pagina !== grupoActual) {
      grupoActual = d.pagina;
      const t = document.createElement("div");
      t.className = "grupo-detecciones-titulo";
      t.textContent = `Página ${d.pagina + 1}`;
      cont.appendChild(t);
    }
    const cat = estado.categorias.find((c) => c.id === d.categoria);
    const fila = document.createElement("div");
    fila.className = "fila-deteccion" + (d.aprobada ? "" : " descartada");
    fila.dataset.deteccion = d.id;
    fila.innerHTML = `
      <input type="checkbox" ${d.aprobada ? "checked" : ""}>
      <div class="cuerpo-deteccion">
        <div class="texto-deteccion">${escapaHtml(d.texto)}</div>
        <div class="metadatos-deteccion">
          <span class="etiqueta-categoria" style="background:${cat ? cat.color : "#888"}">${cat ? cat.nombre : d.categoria}</span>
          <span class="etiqueta-capa" title="Capa 1: reglas · Capa 2: modelo de lenguaje">capa ${d.capa}</span>
          <span class="etiqueta-confianza">${Math.round(d.confianza * 100)} %</span>
        </div>
        <div class="contexto-deteccion">${escapaHtml(d.contexto)}</div>
      </div>`;
    fila.querySelector("input").addEventListener("click", (ev) => {
      ev.stopPropagation();
      alternarDeteccion(d.id, ev.target.checked);
    });
    fila.addEventListener("click", () => desplazarADeteccion(d));
    cont.appendChild(fila);
  }

  if (!ordenadas.length) {
    const p = document.createElement("p");
    p.className = "texto-suave";
    p.textContent = "No se ha detectado ningún dato personal con los interruptores actuales.";
    cont.appendChild(p);
  }
  actualizarContador();
}

function desplazarADeteccion(d) {
  // Todos los rectángulos/marcas de la detección (puede ocupar varias líneas)
  const objetivos = [...document.querySelectorAll(
    `.resaltado[data-deteccion="${d.id}"], mark[data-deteccion="${d.id}"]`)];
  if (!objetivos.length) return;
  objetivos[0].scrollIntoView({ behavior: "smooth", block: "center" });
  for (const o of objetivos) {
    o.classList.remove("flash");
    void o.offsetWidth;              // reinicia la animación si ya estaba
    o.classList.add("flash");
    o.addEventListener("animationend", () => o.classList.remove("flash"), { once: true });
  }
}

// Sincronización inversa: al clicar un resaltado en el documento, localiza y
// destaca su fila en el panel derecho.
function localizarFilaPanel(id) {
  const fila = document.querySelector(`.fila-deteccion[data-deteccion="${id}"]`);
  if (!fila) return;
  fila.scrollIntoView({ behavior: "smooth", block: "nearest" });
  fila.classList.remove("flash-fila");
  void fila.offsetWidth;
  fila.classList.add("flash-fila");
  fila.addEventListener("animationend", () => fila.classList.remove("flash-fila"), { once: true });
}

function escapaHtml(s) {
  const div = document.createElement("div");
  div.textContent = s;
  return div.innerHTML;
}

// ───────────────────────── redacción ─────────────────────────
function abrirConfirmacion() {
  const n = [...estado.detecciones.values()].filter((d) => d.aprobada).length
    + estado.zonasManuales.length + estado.textosManuales.length;
  if (!n) { alert("No hay nada marcado para redactar."); return; }
  $("resumen-redacciones").textContent =
    `${n} elemento${n === 1 ? "" : "s"}`;
  // Nota sobre las opciones de fechas/edad elegidas
  const notas = [];
  if ($("opcion-fechas").value === "desplazar") {
    notas.push("Las fechas de asistencia se sustituirán por fechas desplazadas un número aleatorio de días (la cronología se conserva).");
  }
  if ($("opcion-edad").value === "rango") {
    notas.push("La edad exacta se sustituirá por su rango etario; la fecha de nacimiento se tacha siempre.");
  }
  $("nota-opciones").textContent = notas.join(" ");
  $("nota-opciones").classList.toggle("oculto", !notas.length);
  $("contenido-confirmacion").classList.remove("oculto");
  $("contenido-resultado").classList.add("oculto");
  $("dialogo-resultado").showModal();
}

async function confirmarRedaccion() {
  $("boton-confirmar-redaccion").disabled = true;
  const cuerpo = {
    aprobadas: [...estado.detecciones.values()].filter((d) => d.aprobada).map((d) => d.id),
    zonas_manuales: estado.zonasManuales.map(({ pagina, x0, y0, x1, y1 }) => ({ pagina, x0, y0, x1, y1 })),
    textos_manuales: estado.textosManuales,
    opciones: {
      fechas: $("opcion-fechas").value,
      edad: $("opcion-edad").value,
    },
  };
  const r = await fetch(`/api/documentos/${estado.doc.id}/redactar`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(cuerpo),
  });
  $("boton-confirmar-redaccion").disabled = false;
  if (!r.ok) {
    const err = await r.json().catch(() => ({ detail: "Error desconocido." }));
    alert("No se pudo redactar:\n\n" + err.detail);
    $("dialogo-resultado").close();
    return;
  }
  const datos = await r.json();
  const avisos = $("avisos-verificacion");
  avisos.innerHTML = "";
  if (datos.avisos.length) {
    for (const a of datos.avisos) {
      const div = document.createElement("div");
      div.className = "aviso-residuo";
      div.textContent = "⚠️ " + a;
      avisos.appendChild(div);
    }
  } else {
    const p = document.createElement("p");
    p.textContent = `Se han redactado ${datos.num_redacciones} elementos. ` +
      "La comprobación posterior no encontró restos del texto redactado en el archivo final.";
    avisos.appendChild(p);
  }

  // Segunda pasada: posibles datos personales que quedaron sin marcar
  const residuales = $("residuales-verificacion");
  residuales.innerHTML = "";
  if ((datos.residuales || []).length) {
    const caja = document.createElement("div");
    caja.className = "caja-residuales";
    caja.innerHTML = "<strong>🔍 La segunda pasada encontró posibles datos sin redactar:</strong>";
    const ul = document.createElement("ul");
    for (const r of datos.residuales) {
      const cat = estado.categorias.find((c) => c.id === r.categoria);
      const li = document.createElement("li");
      li.innerHTML = `${escapaHtml(r.texto)} <span class="etiqueta-capa">${escapaHtml(cat ? cat.nombre : r.categoria)}</span> `;
      const boton = document.createElement("button");
      boton.className = "boton-enlace";
      boton.textContent = "redactar también";
      boton.addEventListener("click", () => {
        if (!estado.textosManuales.includes(r.texto)) estado.textosManuales.push(r.texto);
        boton.textContent = "añadido ✓";
        boton.disabled = true;
        pintarListaDetecciones();
      });
      li.appendChild(boton);
      ul.appendChild(li);
    }
    caja.appendChild(ul);
    const nota = document.createElement("p");
    nota.className = "texto-suave";
    nota.textContent = "Si añades alguno, cierra este diálogo y vuelve a pulsar «Aplicar redacción» para generar el documento de nuevo.";
    caja.appendChild(nota);
    residuales.appendChild(caja);
  }

  $("enlace-descarga").href = datos.url_descarga;
  $("enlace-auditoria").href = datos.url_auditoria;
  $("contenido-confirmacion").classList.add("oculto");
  $("contenido-resultado").classList.remove("oculto");
}

// ───────────────────────── ciclo de vida del documento ─────────────────────────
function cerrarDocumento(avisarServidor = true) {
  if (avisarServidor && estado.doc) {
    fetch(`/api/documentos/${estado.doc.id}`, { method: "DELETE" }).catch(() => {});
  }
  estado.doc = null;
  estado.detecciones = new Map();
  estado.zonasManuales = [];
  estado.textosManuales = [];
  estado.escalas = new Map();
  desactivarModoDibujo();
  $("contenedor-paginas").innerHTML = "";
  $("area-documento").classList.add("oculto");
  $("panel-detecciones").classList.add("oculto");
  $("boton-reanalizar").classList.add("oculto");
  $("zona-soltar").classList.remove("oculto");
  procesarSiguienteDeCola();
}

function procesarSiguienteDeCola() {
  if (estado.cola.length) subirArchivo(estado.cola.shift());
}

function mostrarProgreso(texto) {
  $("texto-progreso").textContent = texto;
  $("indicador-progreso").classList.remove("oculto");
  $("zona-soltar").classList.add("oculto");
  $("area-documento").classList.add("oculto");
}
function ocultarProgreso() { $("indicador-progreso").classList.add("oculto"); }

function desactivarModoDibujo() {
  estado.modoDibujo = false;
  $("boton-zona-manual").classList.remove("activo");
  document.querySelectorAll(".capa-resaltados").forEach((c) => c.classList.remove("modo-dibujo"));
}

// ───────────────────────── tema claro/oscuro ─────────────────────────
function aplicarTemaGuardado() {
  const guardado = localStorage.getItem("anonipro_tema");
  const oscuro = guardado ? guardado === "oscuro"
    : window.matchMedia("(prefers-color-scheme: dark)").matches;
  document.documentElement.dataset.tema = oscuro ? "oscuro" : "claro";
}

// ───────────────────────── eventos ─────────────────────────
function conectarEventos() {
  const zona = $("zona-soltar");
  zona.addEventListener("dragover", (ev) => { ev.preventDefault(); zona.classList.add("arrastrando"); });
  zona.addEventListener("dragleave", () => zona.classList.remove("arrastrando"));
  zona.addEventListener("drop", async (ev) => {
    ev.preventDefault();
    zona.classList.remove("arrastrando");
    // Admite soltar CARPETAS completas (se recorren recursivamente)
    const items = [...(ev.dataTransfer.items || [])];
    const entradas = items.map((i) => i.webkitGetAsEntry && i.webkitGetAsEntry()).filter(Boolean);
    if (entradas.some((e) => e.isDirectory)) {
      const archivos = [];
      for (const e of entradas) await recogerDeEntrada(e, archivos);
      recibirArchivos(archivos);
    } else {
      recibirArchivos([...ev.dataTransfer.files]);
    }
  });
  $("boton-elegir").addEventListener("click", () => $("entrada-archivo").click());
  $("entrada-archivo").addEventListener("change", (ev) => recibirArchivos([...ev.target.files]));

  $("boton-tema").addEventListener("click", () => {
    const nuevo = document.documentElement.dataset.tema === "oscuro" ? "claro" : "oscuro";
    document.documentElement.dataset.tema = nuevo;
    localStorage.setItem("anonipro_tema", nuevo);
  });

  $("selector-perfil").addEventListener("change", (ev) => aplicarPerfil(ev.target.value));
  $("boton-guardar-perfil").addEventListener("click", guardarPerfilActual);
  $("boton-reanalizar").addEventListener("click", reanalizar);
  $("boton-mas-negra").addEventListener("click", () => anadirCasilla("lista-negra").focus());
  $("boton-mas-blanca").addEventListener("click", () => anadirCasilla("lista-blanca").focus());

  $("boton-zona-manual").addEventListener("click", () => {
    estado.modoDibujo = !estado.modoDibujo;
    $("boton-zona-manual").classList.toggle("activo", estado.modoDibujo);
    document.querySelectorAll(".capa-resaltados")
      .forEach((c) => c.classList.toggle("modo-dibujo", estado.modoDibujo));
  });

  $("boton-anadir-texto").addEventListener("click", anadirTextoManual);
  $("campo-texto-manual").addEventListener("keydown", (ev) => {
    if (ev.key === "Enter") anadirTextoManual();
  });

  $("boton-marcar-todo").addEventListener("click", () => {
    estado.detecciones.forEach((d, id) => alternarDeteccion(id, true));
  });
  $("boton-desmarcar-todo").addEventListener("click", () => {
    estado.detecciones.forEach((d, id) => alternarDeteccion(id, false));
  });

  $("boton-aplicar").addEventListener("click", abrirConfirmacion);
  $("boton-cancelar-redaccion").addEventListener("click", () => $("dialogo-resultado").close());
  $("boton-confirmar-redaccion").addEventListener("click", confirmarRedaccion);
  $("boton-cerrar-dialogo").addEventListener("click", () => $("dialogo-resultado").close());
  $("boton-cerrar-doc").addEventListener("click", () => {
    if (confirm("Se borrará este documento de la memoria del servidor. ¿Continuar?")) {
      cerrarDocumento();
    }
  });

  // Capa 3 (IA local) y diagnóstico
  $("boton-diagnostico").addEventListener("click", abrirDiagnostico);
  $("boton-cerrar-diagnostico").addEventListener("click", () => $("dialogo-diagnostico").close());
  $("boton-ajustes-ia").addEventListener("click", abrirAjustesIA);
  $("boton-cerrar-ajustes-ia").addEventListener("click", () => $("dialogo-ajustes-ia").close());
  $("boton-buscar-endpoints").addEventListener("click", () => cargarEndpoints(true));
  $("boton-probar-ia").addEventListener("click", probarIA);
  $("boton-guardar-ia").addEventListener("click", guardarIA);
  $("select-endpoint").addEventListener("change", (ev) => {
    if (ev.target.value) { $("input-endpoint").value = ev.target.value; poblarModelosDeSeleccion(); }
  });
}

// ───────────────────────── capa 3: diagnóstico ─────────────────────────
async function abrirDiagnostico() {
  $("dialogo-diagnostico").showModal();
  $("cuerpo-diagnostico").innerHTML = '<p class="texto-suave">Comprobando tu equipo…</p>';
  try {
    const d = await (await fetch("/api/diagnostico")).json();
    $("cuerpo-diagnostico").innerHTML = pintarDiagnostico(d.hardware, d.recomendacion);
    document.querySelectorAll("#cuerpo-diagnostico .boton-copiar").forEach((b) =>
      b.addEventListener("click", () => copiarComandos(b.dataset.comandos)));
  } catch (e) {
    $("cuerpo-diagnostico").innerHTML = '<p class="texto-error">No se pudo comprobar el equipo.</p>';
  }
}

function pintarDiagnostico(hw, rec) {
  const filas = [
    ["Sistema", `${hw.sistema} ${hw.version_so}`],
    ["Procesador", `${hw.cpu} · ${hw.nucleos_logicos || "?"} núcleos`],
    ["Memoria (RAM)", hw.ram_total_gb ? `${hw.ram_total_gb} GB (libres ahora: ${hw.ram_disponible_gb ?? "?"} GB)` : "desconocida"],
    ["Aceleración", hw.aceleracion],
  ];
  let html = '<table class="tabla-diag">' +
    filas.map(([k, v]) => `<tr><td>${k}</td><td>${escapaHtml(v)}</td></tr>`).join("") +
    "</table>";
  html += `<div class="caja-recomendacion">${formatearNegritas(escapaHtml(rec.resumen))}</div>`;
  if (rec.nota_nas) html += `<p class="texto-suave">${escapaHtml(rec.nota_nas)}</p>`;
  for (const paso of rec.pasos) {
    const cmds = paso.comandos.join("\n");
    html += `<div class="bloque-pasos">
      <div class="titulo-pasos">${escapaHtml(paso.titulo)} <span class="etiqueta-capa">${escapaHtml(paso.sistema)}</span></div>
      <pre class="comandos">${escapaHtml(cmds)}</pre>
      <button class="boton-enlace boton-copiar" data-comandos="${escapaHtml(cmds)}">📋 Copiar comandos</button>
    </div>`;
  }
  html += '<p class="texto-suave">Tras instalarlo, abre <strong>⚙️ Ajustes de IA</strong>, elige el servidor y pulsa <strong>Probar</strong>.</p>';
  return html;
}

function copiarComandos(texto) {
  const t = document.createElement("textarea");
  t.innerHTML = texto;
  navigator.clipboard?.writeText(t.value).then(
    () => alert("Comandos copiados al portapapeles."),
    () => {});
}

// ───────────────────────── capa 3: ajustes ─────────────────────────
let endpointsDetectados = [];

async function abrirAjustesIA() {
  $("dialogo-ajustes-ia").showModal();
  $("resultado-prueba-ia").classList.add("oculto");
  const est = await (await fetch("/api/capa3/estado")).json();
  $("input-endpoint").value = est.config.endpoint || "";
  $("check-activar-ia").checked = est.config.activa;
  $("input-modelo").value = est.config.modelo || "";
  await cargarEndpoints(false, est.config.modelo);
}

async function cargarEndpoints(rebuscar, modeloPreferido) {
  const sel = $("select-endpoint");
  sel.innerHTML = '<option value="">Buscando…</option>';
  const extra = $("input-endpoint").value.trim();
  const est = await (await fetch("/api/capa3/estado?extra=" + encodeURIComponent(extra))).json();
  endpointsDetectados = est.endpoints;
  sel.innerHTML = "";
  if (!endpointsDetectados.length) {
    sel.innerHTML = '<option value="">— no se encontró ningún servidor —</option>';
  } else {
    for (const e of endpointsDetectados) {
      const op = document.createElement("option");
      op.value = e.endpoint;
      op.textContent = `${e.tipo} · ${e.endpoint} (${e.modelos.length} modelos)`;
      sel.appendChild(op);
    }
    if (!$("input-endpoint").value) $("input-endpoint").value = endpointsDetectados[0].endpoint;
  }
  poblarModelosDeSeleccion(modeloPreferido);
}

function poblarModelosDeSeleccion(modeloPreferido) {
  const lista = $("lista-modelos");
  const endpoint = $("input-endpoint").value.trim();
  const enc = endpointsDetectados.find((e) => e.endpoint === endpoint);
  const modelos = enc ? enc.modelos : [];
  lista.innerHTML = modelos.map((m) => `<option value="${m}">`).join("");
  if (modeloPreferido && modelos.includes(modeloPreferido)) $("input-modelo").value = modeloPreferido;
  else if (!$("input-modelo").value && modelos.length) $("input-modelo").value = modelos[0];
}

async function probarIA() {
  const endpoint = $("input-endpoint").value.trim();
  const modelo = $("input-modelo").value.trim();
  const caja = $("resultado-prueba-ia");
  caja.classList.remove("oculto");
  caja.className = "resultado-prueba";
  caja.textContent = "Probando…";
  try {
    const r = await (await fetch("/api/capa3/probar", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ endpoint, modelo }),
    })).json();
    if (r.ok) {
      caja.classList.add("ok");
      caja.textContent = `✅ Funciona (${r.latencia_ms} ms). El modelo respondió: «${r.respuesta}»`;
    } else {
      caja.classList.add("mal");
      caja.textContent = "❌ " + r.error;
    }
  } catch (e) {
    caja.classList.add("mal");
    caja.textContent = "❌ No se pudo probar la conexión.";
  }
}

async function guardarIA() {
  const cuerpo = {
    activa: $("check-activar-ia").checked,
    endpoint: $("input-endpoint").value.trim(),
    modelo: $("input-modelo").value.trim(),
  };
  await fetch("/api/capa3/configurar", {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(cuerpo),
  });
  $("dialogo-ajustes-ia").close();
  actualizarEstadoCapa3(cuerpo);
  if (estado.doc) marcarAjustesSucios();
}

function actualizarEstadoCapa3(cfg) {
  const el = $("estado-capa3");
  if (cfg && cfg.activa && cfg.endpoint && cfg.modelo) {
    el.textContent = `IA local: activada (${cfg.modelo})`;
    el.classList.add("activa");
  } else {
    el.textContent = "IA local: desactivada";
    el.classList.remove("activa");
  }
}

function formatearNegritas(s) {
  return s.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
}

// Recorre recursivamente una entrada de carpeta soltada y recoge sus archivos
async function recogerDeEntrada(entrada, archivos) {
  if (entrada.isFile) {
    const f = await new Promise((res, rej) => entrada.file(res, rej)).catch(() => null);
    if (f) archivos.push(f);
  } else if (entrada.isDirectory) {
    const lector = entrada.createReader();
    // readEntries devuelve por tandas: hay que llamar hasta que venga vacío
    let tanda;
    do {
      tanda = await new Promise((res) => lector.readEntries(res, () => res([])));
      for (const e of tanda) await recogerDeEntrada(e, archivos);
    } while (tanda.length);
  }
}

function recibirArchivos(archivos) {
  const validos = archivos.filter((a) => /\.(pdf|docx|jpe?g|png|tiff?|bmp|webp)$/i.test(a.name));
  if (!validos.length) {
    alert("Formato no compatible. Usa PDF, Word (.docx) o una imagen (JPG, PNG, TIFF).");
    return;
  }
  estado.cola.push(...validos.slice(1));
  subirArchivo(validos[0]);
}

function anadirTextoManual() {
  const texto = $("campo-texto-manual").value.trim();
  if (!texto) return;
  estado.textosManuales.push(texto);
  $("campo-texto-manual").value = "";
  pintarListaDetecciones();
}

iniciar();
