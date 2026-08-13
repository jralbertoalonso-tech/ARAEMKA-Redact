<div align="center">

<img src="frontend/iconos/icono-128.png" width="104" alt="AnoniPRO">

# AnoniPRO

**Anonimiza cualquier documento sin que los datos salgan de tu ordenador.**

Informes clínicos · Escritos jurídicos · Nóminas y contratos · Facturas · Papeles personales

*Nodo Local — Dr. José Ramón Alberto Alonso*

</div>

---

## Qué hace

Subes un documento, AnoniPRO **te enseña** todos los datos personales que ha
encontrado, **tú revisas y confirmas**, y descargas una copia con esos datos
**borrados de verdad** del archivo.

No los tapa con un rectángulo negro: los **elimina**. No se pueden recuperar
copiando, pegando ni quitando la marca.

**Todo ocurre en tu equipo.** Sin internet, sin cuentas, sin enviar nada a
ningún sitio. Los documentos ni siquiera se guardan en el disco: se procesan en
memoria y se borran solos.

| Admite | Detecta | Idiomas |
|---|---|---|
| PDF, PDF escaneado, Word (.docx), imágenes (JPG, PNG, TIFF) | 29 tipos de datos personales, agrupados en 8 perfiles | Español e inglés (Reino Unido y EE. UU.), con el idioma del documento detectado automáticamente |

---

## Instalación

Elige **una** forma según dónde lo vayas a usar.

### 🖥️ En tu Mac o tu PC — la más sencilla

1. Descomprime el archivo portable para tu sistema (`AnoniPRO-portable-mac.zip`
   o `AnoniPRO-portable-windows-x64-v…zip`).
2. Doble clic en **`AnoniPRO`** (en Windows, `AnoniPRO.exe`).
3. Se abre el navegador solo. Ya está.

No instala nada ni pide permisos de administrador. La primera vez tarda un
minuto en arrancar.

> **En un Mac que no sea el tuyo**, macOS avisará de que la aplicación «está
> dañada» (no lo está: es que no está firmada). Dentro de la carpeta hay un
> archivo **«PRIMERA VEZ — Abrir aquí»**: clic **derecho** sobre él → **Abrir**.
> Si el aviso persiste, ve a *Ajustes del Sistema → Privacidad y seguridad* y
> pulsa **«Abrir igualmente»**. Solo hace falta la primera vez.

### 🌐 En un servidor o NAS — para todo un equipo de trabajo

Todos los ordenadores de la red lo usan desde el navegador, **sin instalar nada
en ellos**. Ideal para consultas, despachos u oficinas con equipos bloqueados.

👉 Instrucciones paso a paso: **[docs/INSTALAR-EN-NAS.md](docs/INSTALAR-EN-NAS.md)**

### 🛠️ Desde el código fuente

Para desarrolladores o para compilar tus propios paquetes:
**[docs/PARA-DESARROLLADORES.md](docs/PARA-DESARROLLADORES.md)**

---

## Cómo se usa

1. **Arrastra** el documento a la ventana (o varios, o una carpeta entera).
2. Elige un **perfil** en el panel izquierdo según el tipo de documento.
3. **Revisa** la lista de la derecha: cada dato encontrado aparece resaltado
   sobre el documento. Desmarca lo que NO quieras borrar y añade a mano lo que
   se haya escapado.
4. Pulsa **Aplicar redacción** y confirma.
5. AnoniPRO realiza una segunda comprobación automática y te avisa si encuentra
   posibles residuos. **Revisa el resultado completo** y descárgalo solo cuando
   estés conforme.

Nada se borra sin que tú lo confirmes.

---

## Perfiles

Cada perfil enciende los datos que importan en ese tipo de documento. Puedes
retocarlos y guardar los tuyos.

| Perfil | Para qué | Qué protege, además de nombres, DNI, dirección, teléfono y correo |
|---|---|---|
| **Documento clínico** | Historias, informes | Tarjeta sanitaria, nº de historia y episodio, nº de la Seguridad Social |
| **Publicación científica** | Artículos, congresos | Lo anterior **más** hospital, servicio, médicos, nº de colegiado y fechas |
| **Docencia** | Sesiones y material docente | Como el anterior, conservando la estructura del caso |
| **Jurídico** | Contratos, escritos, notaría | Expedientes y autos, protocolo, catastro y fincas, matrículas, IBAN, CIF, juzgados |
| **Empresa y RR. HH.** | Nóminas, contratos laborales | Seguridad Social, IBAN, CIF, nº de empleado, matrículas, razón social |
| **Facturas y contabilidad** | Facturas, presupuestos | CIF/NIF, IBAN, tarjetas, nº de factura y datos del cliente |
| **Documento personal** | Tus propios papeles | IBAN, tarjetas, Seguridad Social, matrícula, catastro |
| **Todo activado** | Máxima protección | Absolutamente todo |

### Los 26 tipos de datos que reconoce

- **Identidad** — nombres (también tras su cargo: «Cliente:», «Demandante:»), DNI/NIE, pasaporte, fecha de nacimiento, edad, sexo.
- **Contacto** — direcciones, teléfonos, correos, localidades y códigos postales.
- **Económicos** — cuentas IBAN, tarjetas de pago, CIF/NIF de empresa.
- **Salud** — tarjeta sanitaria (incluido T.I.S.), nº de historia y episodio, Seguridad Social, personal sanitario, nº de colegiado, hospitales y servicios.
- **Trámites y bienes** — expedientes, autos judiciales, protocolo notarial, pólizas, contratos, facturas, referencia catastral, fincas y matrículas.
- **Organizaciones** — empresas, juzgados, notarías, registros y los logotipos del membrete.

Los identificadores con dígito de control (**DNI, NIE, Seguridad Social, IBAN,
CIF, tarjetas**) se comprueban **matemáticamente**: si el control no cuadra, no
se marcan. Así no se señalan números que solo se parecen.

### Además puedes

- **Desplazar las fechas** en vez de borrarlas: todas se mueven los mismos días
  al azar, así se conserva el orden y los intervalos sin revelar las reales.
- **Sustituir la edad exacta por un rango** («47 años» → «45-49 años»).
- Descargar un **informe de auditoría** de qué se borró y con qué ajustes (sin
  incluir ningún dato original).

---

## Por qué es privado

- **Nada sale de tu equipo.** Ninguna parte del programa se conecta a internet.
  Puedes desconectar la red y sigue funcionando igual.
- **Nada se guarda en disco.** Los documentos viven en la memoria y se borran
  solos a a los 30 minutos, o cuando pulsas *Terminar*.
- **El borrado es real.** En PDF se elimina el texto de la capa de contenido; en
  escaneados e imágenes se borran los píxeles; en Word se sustituye dentro del
  archivo. También se limpian los metadatos ocultos (autor, título…).
- **Se realiza una segunda comprobación automática.** Tras borrar, el resultado
  se vuelve a analizar para buscar coincidencias y posibles datos residuales.
  Esta comprobación ayuda a revisar, pero no certifica que no quede ningún dato.

---

## Cómo encuentra los datos

Tres capas que se complementan:

| Capa | Qué es |
|---|---|
| **1 · Reglas** | Patrones españoles con validación de dígitos de control: DNI, Seguridad Social, IBAN, CIF, tarjetas, tarjeta sanitaria, teléfonos, catastro, matrículas… |
| **2 · Modelo de nombres** | Un modelo de lenguaje en español que reconoce nombres, lugares y organizaciones aunque no tengan un formato fijo. Funciona sin tarjeta gráfica. |
| **3 · IA local** *(opcional)* | Un modelo de IA que corre **en tu propia red** (Ollama o LM Studio) para menciones indirectas y nombres poco frecuentes. Se activa y desactiva; todo funciona sin él. |

Si el documento está **escaneado o es una imagen**, antes pasa por
reconocimiento óptico (OCR) en tu propio equipo.

---

## Si algo no va

| Qué ocurre | Qué hacer |
|---|---|
| macOS dice que la app «está dañada» | No lo está. Usa «PRIMERA VEZ — Abrir aquí» (arriba lo explica) |
| Windows muestra «Windows protegió su PC» | Comprueba el SHA-256 publicado con el ZIP; si coincide, pulsa «Más información» → «Ejecutar de todas formas» |
| La ventana negra se cierra sola | Es la aplicación: déjala abierta mientras la uses |
| Un PDF escaneado no se lee | En Windows y NAS el OCR ya viene incluido. En Mac: `brew install tesseract tesseract-lang` |
| Marca cosas que no son datos | Escríbelas en «No redactar nunca estos términos» del panel izquierdo |
| No detecta un dato tuyo | Añádelo a mano en el panel derecho, o a «Redactar siempre estos términos» |
| Sale «El documento caducó» | Ha pasado el tiempo de seguridad y se borró de la memoria: vuelve a subirlo |

---

## Lo que todavía no hace

Dicho claramente, para que nadie se lleve sorpresas:

- **No abre archivos `.doc` antiguos** (Word 97-2003). Ábrelos en Word y
  guárdalos como `.docx`.
- **El OCR no es perfecto.** En documentos escaneados puede leer mal algún dato,
  sobre todo los correos electrónicos (la `@` se le resiste). Por eso conviene
  revisar y usar el marcado a mano.
- **Idiomas: español e inglés.** El programa detecta solo el idioma de cada
  documento y aplica el motor adecuado. En español reconoce los identificadores
  españoles (DNI, Seguridad Social, tarjeta sanitaria, catastro…); en inglés,
  los del **Reino Unido y EE. UU.** (NHS, National Insurance, SSN/ITIN, códigos
  postales y teléfonos). Otros idiomas no están soportados.
- **Revisa siempre antes de compartir.** Ninguna herramienta automática es
  infalible: AnoniPRO te enseña lo que ha encontrado precisamente para que la
  decisión final sea tuya.

---

## Advertencia sobre los resultados y responsabilidad

AnoniPRO es una **herramienta de apoyo**: no garantiza la detección o eliminación
completa de todos los datos personales. El OCR, los modelos lingüísticos y las
reglas automáticas pueden omitir información, interpretarla incorrectamente o
dejar elementos visibles o susceptibles de reidentificación.

El resultado debe revisarse íntegramente antes de compartirlo, publicarlo o
utilizarlo. Cuando corresponda, la persona u organización responsable del
tratamiento conserva sus obligaciones legales y debe valorar el riesgo y
aplicar las medidas adicionales adecuadas al caso concreto.

En la máxima medida permitida por la legislación aplicable, el autor no responde
de daños indirectos derivados de un uso incorrecto, de la falta de revisión o de
usos no previstos. Esta limitación no excluye las responsabilidades ni los
derechos que legalmente no puedan limitarse.

Consulta las condiciones completas en **[AVISO-LEGAL.md](AVISO-LEGAL.md)**. Antes
de una distribución comercial, institucional o pública deben adaptarse al modelo
de licencia y revisarse por un profesional jurídico cualificado.

---

## Licencia y componentes

El código de AnoniPRO es obra del autor; **todos los derechos reservados**.

Utiliza componentes libres de terceros, cuya autoría corresponde a sus
respectivos titulares: FastAPI, Microsoft Presidio, spaCy, PyMuPDF (AGPL-3.0),
python-docx, Tesseract OCR, Pillow y PDF.js. Los modelos de lenguaje y de IA se
distribuyen bajo sus propias licencias.

---

<div align="center">
<sub>AnoniPRO · Nodo Local · Procesamiento 100 % local, sin conexión a internet</sub>
</div>
