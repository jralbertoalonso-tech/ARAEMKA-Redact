# 🩺 AnoniPRO — Anonimización local de documentos clínicos

**Autor: Dr. José Ramón Alberto Alonso**

Aplicación **100 % local** para anonimizar informes clínicos (PDF y Word) sin que
ningún dato salga de tu equipo o de tu red. Sin telemetría, sin llamadas a
servicios externos, sin cuentas. Una vez instalada, funciona **sin conexión a
internet**.

Pensada para uso médico: interfaz en español, clara y sin jerga técnica.

> **Estado actual: Fase 5 (proyecto completo).** Todo lo de las fases 1-4
> (OCR, tres capas, auditoría, segunda pasada, lotes, métricas, portable) más:
> **desplazamiento aleatorio consistente de fechas** (conserva la cronología
> clínica) y **rango etario en lugar de edad exacta**, elegibles en el panel
> «Fechas y edad».

---

## ¿Qué hace, en una frase?

Subes un informe, la aplicación **te muestra** todos los datos personales que ha
encontrado (nombre del paciente, DNI, teléfono, historia clínica, médicos,
hospital…), **tú revisas y confirmas**, y descarga una copia con esos datos
**eliminados de verdad** del archivo (no tapados con un rectángulo: borrados, no
se pueden recuperar copiando ni pegando).

---

## Instalación

Elige **una** de las tres formas según dónde quieras usarlo.

### (a) En el NAS Synology (DS923+, DSM 7.x) — modo servidor recomendado

Así lo usan varios usuarios a la vez desde cualquier PC de la red, **sin instalar
nada en esos PC** (solo el navegador).

1. **Copia el proyecto al NAS.** Pon toda la carpeta `AnoniPRO` en una carpeta
   compartida, por ejemplo `docker/anonipro`, usando File Station o una unidad de
   red.
2. **Abre Container Manager** (Centro de paquetes → si no lo tienes, instálalo).
3. Ve a **Proyecto → Crear**.
   - **Nombre del proyecto:** `anonipro`
   - **Ruta:** selecciona la carpeta que copiaste.
   - **Origen:** «Usar un docker-compose.yml existente» → elige el
     `docker-compose.yml` de la carpeta.
4. Pulsa **Siguiente** y **Hecho**. La primera vez, el NAS **construye la imagen**
   (descarga Python y el modelo de detección); tarda entre 5 y 15 minutos y
   necesita internet **solo esta vez**.
5. Cuando el proyecto aparezca como **en ejecución**, abre desde cualquier
   navegador de la red:
   ```
   http://IP-DE-TU-NAS:8080
   ```
   (La IP del NAS la ves en DSM → Panel de control → Red, o en la app Synology.)

**Contraseña de acceso (recomendada en el NAS):** edita `docker-compose.yml`
antes de crear el proyecto y pon algo en `ANONIPRO_PASSWORD: "loquesea"`. Como el
NAS puede ser accesible por más gente, conviene activarla.

> Tu NAS tiene 32 GB de RAM, de sobra para el modelo grande (`es_core_news_lg`)
> que ya viene configurado. El propio NAS ejecuta las capas 1 y 2. La capa 3 (LLM)
> **no corre en el NAS** —no tiene GPU—; en la Fase 3 se explica cómo delegarla a
> tu Mac con Ollama/LM Studio.

### (b) En tu Mac (Apple Silicon) — modo local

1. Haz **doble clic** en `iniciar_mac.command` (dentro de la carpeta del
   proyecto). La primera vez prepara el entorno y descarga el modelo (necesita
   internet una vez); las siguientes arranca en segundos.
2. Se abre solo el navegador en `http://localhost:8080`.

Si macOS bloquea el archivo por seguridad: clic derecho → **Abrir** → **Abrir**.

Requisitos:
- **Python 3.10 o superior**. Si no lo tienes, el script te lo dice; instálalo con
  `brew install python@3.12` ([Homebrew](https://brew.sh)).
- Para **escaneados e imágenes (OCR)**, instala Tesseract una vez:
  `brew install tesseract tesseract-lang`. Si no lo instalas, los PDF con texto y
  los `.docx` funcionan igual; solo los escaneados/imágenes lo necesitan.

### (c) Windows / otros — modo local

Con Python 3.10+ instalado, en una terminal dentro de la carpeta del proyecto:

```bat
python -m venv .venv
.venv\Scripts\pip install -r backend\requirements.txt
.venv\Scripts\python -m spacy download es_core_news_lg
.venv\Scripts\python -m uvicorn app.main:app --port 8080 --app-dir backend
```

Luego abre `http://localhost:8080`. (El **ejecutable único sin instalación** para
Windows sin permisos de administrador llega en la Fase 4.)

---

## Cómo se usa (para el médico)

1. **Arrastra** un informe (PDF o `.docx`) a la ventana, o pulsa *Elegir archivo*.
   Puedes soltar varios: se procesan en cola, uno tras otro.
2. En el **panel izquierdo** decides qué tipos de datos anonimizar (interruptores)
   o eliges un **perfil** ya hecho: *Sesión clínica*, *Publicación científica*,
   *Docencia*…
3. En el **panel derecho** aparece la **lista de todo lo detectado**, con su
   categoría, la confianza y la frase donde sale. Se resalta por colores sobre el
   documento.
4. **Revisa**: desmarca lo que NO quieras redactar (falsos positivos), añade a
   mano texto que se haya escapado, o dibuja una zona con *Marcar zona a mano*
   (en PDF).
5. Pulsa **Aplicar redacción**, confirma, y **descarga** el documento anonimizado.
   La aplicación vuelve a escanear el resultado y te avisa si detecta algún resto.

Nada se anonimiza «a ciegas»: **siempre** revisas antes.

---

## Privacidad: cómo está construido

- **No se escribe en disco.** Los documentos viven solo en la memoria del servidor
  y se borran solos a los 30 minutos (configurable) o cuando pulsas *Terminar*.
- **Redacción destructiva de verdad.** En PDF con texto se elimina el texto de la
  capa de contenido (no se tapa); en un escaneado o imagen se **borran los
  píxeles** de la zona; en Word se sustituye por bloques `█` dentro del archivo.
  Se limpian además los metadatos (autor, título…), que suelen llevar nombres.
- **Sin red.** Ninguna dependencia hace llamadas externas en ejecución. Puedes
  cortarle internet al NAS/equipo y sigue funcionando.

---

## Cómo detecta los datos (tres capas)

| Capa | Qué es | Ejemplos que caza |
|------|--------|-------------------|
| **1 — Reglas** | Patrones españoles con **validación de dígitos/letra de control** | DNI/NIE (letra correcta), NUSS (módulo 97), CIP-SNS, teléfonos, emails, fechas, códigos postales canarios, NHC/episodio y nº de colegiado por contexto, direcciones, hospitales y siglas (HUNSC, HUC…), «Dr./Dra./Fdo.» |
| **2 — Modelo de nombres** | Modelo de lenguaje en español (`es_core_news_lg`), **funciona en CPU**, siempre activo | Nombres de personas, lugares y organizaciones poco habituales, sin formato fijo |
| **3 — LLM local (opcional)** | Modelo de IA que corre en tu red (Ollama/LM Studio), **activable y desactivable** | Menciones indirectas y nombres raros que las capas 1-2 no ven (p. ej. «al que llaman el herrero viejo») |

La capa 1 valida los identificadores: un número que «parece» un DNI pero cuya
letra no cuadra **no** se marca, para reducir falsos positivos.

Antes de las capas, si el documento está **escaneado o es una imagen**, pasa por
el **OCR** (Tesseract español) que reconstruye el texto y la posición de cada
palabra; a partir de ahí, las capas 1-2 trabajan igual. Además se detectan los
**logos/membretes** (imágenes en cabecera/pie) por la estructura del PDF.

---

## Probar (validación antes de seguir)

Puedes comprobar que todo funciona con documentos **sintéticos** (datos
inventados, con DNI/NUSS de control válido pero que no pertenecen a nadie).

```bash
# 1) Generar los documentos de prueba (incluye escaneado e imagen para el OCR)
.venv/bin/python herramientas/generar_documentos_prueba.py
#   → informe_alta.pdf, interconsulta.docx, analitica.pdf,
#     informe_alta_ESCANEADO.pdf, analitica_IMAGEN.png

# 2) Ejecutar la batería de pruebas automáticas (validadores + detección +
#    redacción destructiva verificada + OCR). Son 19 pruebas.
cd backend && ../.venv/bin/python -m pytest tests/ -v
```

Después, en la web:

1. Arranca la app (apartado (a)/(b)/(c)) y abre `http://localhost:8080`.
2. Sube `documentos_prueba/informe_alta.pdf`. Comprueba que detecta el nombre de
   la paciente, DNI, NHC, teléfono, dirección, CIP, NUSS, el hospital, el
   servicio, la médico que firma y su nº de colegiado.
3. Desmarca alguna detección, añade un texto a mano, pulsa *Aplicar redacción* y
   descarga el PDF.
4. **Verificación clave:** abre el PDF descargado, intenta **seleccionar y copiar**
   donde estaba el nombre del paciente: no hay texto que copiar; el dato se
   eliminó del archivo.
5. Repite con `interconsulta.docx` para el flujo Word.
6. **Prueba el OCR (Fase 2):** sube `informe_alta_ESCANEADO.pdf` (un PDF sin capa
   de texto) o `analitica_IMAGEN.png`. Aparece el aviso azul de OCR, y los datos
   se detectan y resaltan **sobre la imagen**. Redacta y descarga: sobre la
   imagen la redacción borra los píxeles (la zona queda negra de verdad).
7. **Prueba la Fase 4:** tras redactar, descarga el **informe de auditoría** y
   ábrelo: verás recuentos y configuración, pero ningún dato del paciente. Si la
   segunda pasada lista «posibles datos sin redactar», prueba el botón «redactar
   también». Y arrastra una **carpeta** con varios documentos para ver la cola.

> La batería `pytest` (31 pruebas) comprueba cada categoría, la redacción
> irreversible, el OCR, la capa 3 y que la auditoría no contiene datos. Las
> **métricas por categoría** se calculan con `herramientas/evaluar_deteccion.py`
> (ver sección de la Fase 4).

---

## OCR: escaneados e imágenes (Fase 2)

Si subes un **PDF escaneado** o una **imagen** (JPG, PNG, TIFF), la app reconoce
el texto con **Tesseract en español**, todo en local. Después el flujo es el
mismo: ves lo detectado resaltado sobre la imagen, revisas y rediges. La
redacción sobre una imagen **borra los píxeles** (no los tapa), y la comprobación
posterior vuelve a pasar OCR para asegurarse de que el dato no reaparece.

- En el **NAS** el OCR ya viene incluido en la imagen Docker: no tienes que hacer
  nada.
- En **macOS**, instálalo una vez con `brew install tesseract tesseract-lang`. Si
  falta, la app te avisa al subir un escaneado (y el indicador «OCR» de la
  cabecera lo muestra).
- La salida de una imagen suelta se entrega en **PDF** (formato universal).

Limitaciones propias del OCR (inevitables, dichas claramente): el reconocimiento
no es perfecto. Los **correos electrónicos** son el caso más frágil (el OCR
suele leer mal la `@`), y un escaneo torcido o de baja calidad puede perder algún
dato. Por eso el aviso azul te recuerda revisar con atención y, si hace falta,
marcar zonas a mano.

## IA local opcional: la capa 3 (Fase 3)

La capa 3 es **opcional** y está **desactivada por defecto**. La app funciona
perfectamente sin ella. Si la activas, usa un modelo de IA que corre **en tu red**
(Ollama o LM Studio) para cazar datos que las reglas y el NER no ven: nombres poco
frecuentes, apodos, menciones indirectas del paciente. El texto se envía solo a
ese equipo de tu red local; **nada sale a internet**.

**Cómo usarla:**

1. Pulsa **🖥️ Comprobar mi equipo**. La app detecta tu sistema, CPU, RAM y
   aceleración (Apple Silicon/Metal, NVIDIA/CUDA o solo CPU) y te dice **qué
   modelo usar y los comandos exactos** para instalarlo (con botón de copiar).
   - Mac Apple Silicon con bastante RAM → **Qwen 3 8B** (`ollama pull qwen3:8b`).
   - Equipo de 8 GB → un modelo más pequeño (Qwen 3 4B / Gemma 3 4B / Llama 3.2 3B).
   - **El NAS no ejecuta el LLM** (no tiene GPU): la app te indica cómo delegarlo
     en otro equipo de tu red.
2. En **⚙️ Ajustes de IA**, elige el servidor detectado (o escribe su dirección:
   Ollama usa el puerto 11434; LM Studio, el 1234), elige el modelo y pulsa
   **Probar** — se hace una petición real y te confirma si responde y en cuánto
   tiempo. Marca **Activar la capa 3** y **Guardar**.
3. Al analizar, las detecciones de la capa 3 aparecen con la etiqueta «capa 3».

**Salvaguardas:** antes de analizar, la app comprueba una vez que el servidor
responde; si está activada pero no contesta, **no se cuelga** — analiza con las
capas 1-2 y te avisa. Como recomienda tu perfil, tú tienes **Ollama y LM Studio**:
cualquiera de los dos vale.

> Los modelos recomendados están verificados a julio de 2026 (familias Qwen 3,
> Gemma 3 y Llama 3.x, las mejores abiertas pequeñas con buen español). El
> catálogo está en `backend/app/detection/diagnostico_hardware.py` por si quieres
> ajustarlo.

## Auditoría, segunda pasada, lotes y portable (Fase 4)

**Informe de auditoría.** Tras redactar, el botón **📋 Informe de auditoría**
descarga un JSON con: fecha/hora, configuración usada (categorías, nº de términos
de las listas), recuento de detecciones por categoría (detectadas/redactadas),
zonas y textos manuales, resultado de la segunda pasada y la huella SHA-256 del
archivo final. **Nunca incluye los datos redactados** (hay una prueba automática
que lo garantiza). Se descarga y lo guardas tú donde quieras: siguiendo el
principio de la app, el servidor no conserva nada en disco.

**Segunda pasada reforzada.** Después de redactar, la app re-escanea el
documento resultante con el motor completo:
1. Comprueba que **ningún texto aprobado** sigue en el archivo (en escaneados,
   re-OCRando el resultado).
2. Busca **posibles datos que nadie marcó** y te los enseña con un botón
   «redactar también» — un clic los añade y vuelves a aplicar. Lo que tú
   **rechazaste expresamente se respeta** (no te lo vuelve a proponer).

**Lotes.** Puedes arrastrar **una carpeta completa** (se recorre entera, con
subcarpetas): los documentos entran en cola y se procesan uno tras otro, cada
uno con su verificación. La barra muestra cuántos quedan.

**Métricas de detección.** El corpus sintético y el cálculo por categoría:
```bash
.venv/bin/python herramientas/evaluar_deteccion.py 40
```
Resultado actual (capas 1-2, sin LLM): **sensibilidad global 99,6 %, precisión
98,4 %**. El punto más débil son localidades pequeñas sueltas (p. ej. «Adeje»),
que es justo lo que la capa 3 ayuda a cubrir. Nota honesta: en detección de
entidades no existe la «especificidad» clásica (no hay un número finito de
verdaderos negativos); la precisión cumple ese papel.

**Modo portable (sin instalación, sin permisos de administrador).**
```bash
# macOS (construye en un Mac):
bash herramientas/construir_portable_mac.sh
# Windows (construye en un Windows; PyInstaller no cross-compila):
herramientas\construir_portable_windows.bat
```
El resultado es una carpeta `dist/AnoniPRO/` (~760 MB, el modelo de lenguaje va
dentro) y un `AnoniPRO-portable-mac.zip` listo para llevar. En el equipo de
destino: descomprimir y doble clic. Abre el navegador solo, escucha únicamente
en 127.0.0.1 (no se expone a la red) y si el puerto 8080 está ocupado elige otro
libre automáticamente. El OCR de escaneados es lo único que necesita Tesseract
instalado aparte (opcional; la app avisa si falta).

**Primer arranque en un Mac nuevo:** macOS marca en cuarentena lo que llega de
otro equipo y, al no estar firmada con certificado de Apple, muestra el aviso de
«dañado y debería ir a la papelera» — no está dañada. Pasos (solo la primera vez):

1. Dentro de la carpeta, clic **derecho** sobre
   **«PRIMERA VEZ — Abrir aquí.command»** → **Abrir**.
2. En macOS recientes (Sequoia y posteriores) saldrá otro aviso: ve a
   **Ajustes del Sistema → Privacidad y seguridad**, baja hasta el mensaje sobre
   el archivo bloqueado y pulsa **«Abrir igualmente»**; vuelve a abrir el
   archivo.
3. El script quita el bloqueo de toda la carpeta y arranca la app (el primer
   arranque tarda ~1 minuto). A partir de entonces basta el **doble clic normal**
   en `AnoniPRO`.

(Transporta siempre el **.zip**, no la carpeta suelta: así no se pierden
permisos ni archivos internos por el camino.)

## Fechas desplazadas y rangos etarios (Fase 5)

En el panel lateral, sección **«Fechas y edad»**, hay dos alternativas a tachar:

- **Fechas de asistencia → Desplazar.** Todas las fechas del documento se
  sustituyen por fechas movidas el MISMO número aleatorio de días (entre 30 y
  180, hacia delante o atrás). La **cronología clínica se conserva** (los días
  entre ingreso, pruebas y alta no cambian), pero las fechas reales desaparecen
  del archivo con la misma redacción destructiva. El desplazamiento es
  consistente dentro del documento y **no se registra en la auditoría** (solo el
  modo), porque conocerlo permitiría reconstruir las fechas reales.
- **Edad exacta → Rango etario.** «47 años» pasa a «45-49 años» (bandas
  quinquenales, práctica habitual en publicaciones); los lactantes quedan como
  «menor de 1 año». La **fecha de nacimiento se tacha siempre** — es un
  identificador demasiado fuerte para desplazarla.

Si una fecha no se puede interpretar con seguridad (formato raro, fecha
imposible), se tacha en negro: ante la duda, lo conservador.

## Otras limitaciones conocidas (dichas claramente)

- **Word `.doc` antiguo (97-2003):** no es compatible. La app te pide guardarlo
  como `.docx`. La conversión automática se valorará para la versión del NAS.
- **Capa 3 en documentos largos:** el LLM revisa página a página; en una historia
  de 40 páginas puede tardar (segundos por página). Es el precio de la revisión
  semántica; para lotes grandes en segundo plano, espera a la Fase 4.
- **Formato dentro de un párrafo Word redactado:** al redactar un párrafo se
  conserva su formato general, pero puede perderse un cambio de formato interno
  (p. ej. una palabra en negrita a mitad de frase). El texto no redactado no se
  toca.
- **NHC, CIP autonómico, nº de episodio y de colegiado:** no tienen un formato
  público único entre centros, así que se detectan **por contexto** (una etiqueta
  como «NHC:», «CIP», «Colegiado» seguida del número). Si un informe usa una
  etiqueta rara, puedes añadir el número a mano o a tu lista de términos.

---

## Hoja de ruta

- **Fase 1 (hecha):** MVP — web local en Docker, PDF con texto + `.docx`, capas
  1-2, interruptores, perfiles, verificación con resaltado, redacción destructiva
  verificada.
- **Fase 2 (hecha):** OCR local (Tesseract español) para PDF escaneados e
  imágenes (JPG/PNG/TIFF), redacción destructiva de píxeles verificada con re-OCR,
  detección de logos/membretes en cabecera/pie.
- **Fase 3 (hecha):** capa 3 LLM local opcional (Ollama/LM Studio) con activar/
  desactivar, detección de endpoints, prueba real del modelo, y módulo de
  diagnóstico de hardware con recomendación de instalación paso a paso.
- **Fase 4 (hecha):** informe de auditoría por documento (sin datos originales),
  segunda pasada de verificación reforzada con «redactar también», lotes por
  carpeta completa, métricas de sensibilidad/precisión por categoría, y modo
  portable para macOS y Windows (scripts de construcción incluidos).
- **Fase 5 (hecha):** desplazamiento aleatorio consistente de fechas (conserva
  la cronología) y sustitución de la edad exacta por rango etario.

**Posibles mejoras futuras** (si las necesitas): conversión automática de `.doc`
antiguos en el NAS (LibreOffice), workers en paralelo para lotes muy grandes, y
sustitución por etiquetas tipo «[PACIENTE]» en lugar de █.

---

## Estructura del proyecto

```
AnoniPRO/
├─ backend/
│  ├─ app/
│  │  ├─ main.py               arranque del servidor web
│  │  ├─ api.py                rutas REST (subir, analizar, redactar, descargar)
│  │  ├─ config.py             configuración por variables de entorno
│  │  ├─ seguridad.py          contraseña opcional
│  │  ├─ almacen.py            documentos en memoria (nunca en disco)
│  │  ├─ detection/            motor de detección
│  │  │  ├─ categorias.py         catálogo de categorías + colores
│  │  │  ├─ validators.py         dígitos/letra de control (DNI, NUSS…)
│  │  │  ├─ reconocedores_es.py   capa 1: reglas españolas y canarias
│  │  │  └─ motor.py              orquesta capa 1 + capa 2 (spaCy)
│  │  └─ documentos/
│  │     ├─ pdf_doc.py            PDF: extracción y redacción destructiva
│  │     └─ docx_doc.py           Word .docx: extracción y redacción
│  ├─ tests/test_mvp.py        batería de pruebas
│  └─ requirements.txt
├─ frontend/                   interfaz (HTML/CSS/JS, servida por el backend)
│  ├─ index.html · styles.css · app.js
│  └─ vendor/pdfjs/            visor de PDF (local, sin CDN)
├─ herramientas/
│  ├─ generar_documentos_prueba.py    documentos sintéticos (incluye escaneados)
│  ├─ evaluar_deteccion.py            métricas de sensibilidad/precisión
│  ├─ construir_portable_mac.sh       portable macOS (PyInstaller)
│  └─ construir_portable_windows.bat  portable Windows (ejecutar en Windows)
├─ backend/portable_main.py           punto de entrada del portable
├─ Dockerfile · docker-compose.yml    despliegue en Synology
└─ iniciar_mac.command                arranque en macOS
```
