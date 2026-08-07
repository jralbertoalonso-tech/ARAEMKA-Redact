# AnoniPRO — Documentación técnica

Todo lo que necesitas para trabajar sobre el código: arrancarlo, probarlo,
entender cómo detecta y generar los paquetes distribuibles.

---

## Arrancar en desarrollo

Requiere **Python 3.10+**.

```bash
python3 -m venv .venv
.venv/bin/pip install -r backend/requirements.txt
.venv/bin/python -m spacy download es_core_news_lg
.venv/bin/python -m uvicorn app.main:app --port 8080 --app-dir backend
```

Luego abre `http://localhost:8080`.

En macOS, `iniciar_mac.command` hace todo lo anterior con doble clic (prepara el
entorno la primera vez y elige un puerto libre si el 8080 está ocupado).

Para el **OCR** hace falta el binario de Tesseract con el idioma español:
`brew install tesseract tesseract-lang` (macOS) o
[UB Mannheim](https://github.com/UB-Mannheim/tesseract/wiki) (Windows).

---

## Estructura

```
backend/
  app/
    main.py          arranque del servidor y archivos estáticos
    api.py           rutas REST (subir, analizar, redactar, auditoría)
    config.py        ajustes por variables de entorno
    seguridad.py     contraseña opcional y límite de intentos
    almacen.py       documentos en memoria, con caducidad
    textos.py        mensajes del servidor en español e inglés
    detection/
      categorias.py            catálogo de datos (una sola fuente de verdad)
      validators.py            dígitos de control: DNI, NUSS, IBAN, CIF, Luhn…
      reconocedores_es.py      capa 1: reglas y expresiones regulares
      motor.py                 orquesta capas 1-2 y resuelve solapamientos
      capa3_llm.py             capa 3: LLM local opcional
      diagnostico_hardware.py  recomendación de modelo según el equipo
    documentos/
      pdf_doc.py       PDF: extracción posicionada y redacción destructiva
      docx_doc.py      Word: extracción y sustitución dentro del XML
      ocr.py           Tesseract
      fechas.py        desplazamiento de fechas y rangos etarios
  tests/             63 pruebas
frontend/            interfaz (HTML/CSS/JS sin framework)
  idiomas.js         todos los textos en español e inglés
  vendor/pdfjs/      visor de PDF (local, sin CDN)
herramientas/        scripts de apoyo (ver más abajo)
docs/                esta documentación
```

**Principios que conviene respetar al tocar el código:**

1. Los documentos **nunca se escriben en disco**.
2. La redacción es **destructiva**: se elimina el contenido, no se tapa.
3. Nada se redacta **sin confirmación** del usuario.
4. Ninguna dependencia hace **llamadas de red** en ejecución (salvo la capa 3,
   que solo puede apuntar a direcciones de red privada).
5. Ante la duda en privacidad, la opción **más conservadora**.

---

## Pruebas

```bash
cd backend && ../.venv/bin/python -m pytest tests/ -v
```

| Archivo | Cubre |
|---|---|
| `test_mvp.py` | Validadores, detección por categoría, redacción destructiva de PDF y docx |
| `test_ocr.py` | OCR, redacción de píxeles verificada con re-OCR, membretes |
| `test_capa3.py` | Diagnóstico de hardware y capa 3 (con el LLM simulado) |
| `test_fase4.py` | Segunda pasada y auditoría (que no contenga datos originales) |
| `test_fase5.py` | Desplazamiento de fechas y rangos etarios |
| `test_universal.py` | IBAN, CIF, tarjetas, matrículas, catastro y perfiles |

### Métricas de detección

```bash
.venv/bin/python herramientas/evaluar_deteccion.py 40
```

Genera un corpus sintético con verdad terreno y mide por categoría.
Resultado actual (capas 1-2, sin IA): **sensibilidad 99,4 %, precisión 97,3 %**.

> En detección de entidades no se puede calcular la «especificidad» clásica (no
> hay un número finito de verdaderos negativos); la precisión cumple ese papel.

### Documentos de prueba

```bash
.venv/bin/python herramientas/generar_documentos_prueba.py
```

Crea informes clínicos, un contrato, una factura y una nómina sintéticos, más un
PDF escaneado y una imagen para probar el OCR. **Todos los datos son inventados**
(los DNI y NUSS llevan dígito de control válido para ejercitar los validadores,
pero no pertenecen a nadie).

---

## Generar los paquetes

| Paquete | Comando | Notas |
|---|---|---|
| Portable macOS | `bash herramientas/construir_portable_mac.sh` | Se autocomprueba: verifica que no quedan enlaces simbólicos, que los módulos compilados están dentro y que **el ejecutable arranca de verdad** antes de darlo por bueno |
| Portable Windows | `herramientas\construir_portable_windows.bat` | **Debe ejecutarse en Windows**: PyInstaller no compila para otra plataforma |
| Imagen para el NAS | `docker buildx build --platform linux/amd64 -t anonipro:latest --load .`<br>`docker save anonipro:latest \| gzip > AnoniPRO-synology/anonipro-imagen.tar.gz` | El DS923+ es AMD64; hay que forzar la plataforma |
| Iconos | `.venv/bin/python herramientas/generar_iconos.py` | Genera `.icns`, `.ico` y PNG desde `frontend/icono.svg`. Los dos empaquetadores ya lo llaman |

**Lecciones aprendidas empaquetando** (para no repetirlas):

- PyInstaller puede dejar fuera módulos compilados de spaCy (`cymem`, `thinc`…)
  aunque estén declarados: por eso se fuerzan y se comprueban.
- Los enlaces simbólicos internos se rompen al copiar la carpeta entre discos:
  el script los convierte en archivos reales.
- Distribuye siempre el **.zip**, nunca la carpeta suelta.
- En macOS la app no está firmada: hace falta el desbloqueo de cuarentena que ya
  incluye el paquete.

---

## Cómo funciona la detección

### Capa 1 — Reglas

`reconocedores_es.py`. Cada identificador con dígito de control se valida
matemáticamente en `validators.py`; si no cuadra, **se descarta**. Los que no
tienen formato público estable (nº de historia, expedientes, colegiado…) se
detectan por su **etiqueta** («NHC:», «Expediente nº», «Cliente:»), que es lo
más fiable cuando el formato varía entre organizaciones.

> ⚠️ **Presidio aplica `re.IGNORECASE` por defecto.** Para los patrones donde
> las mayúsculas son la señal (nombres de sociedad, IBAN, catastro) hay que
> pasar `global_regex_flags=re.MULTILINE | re.DOTALL`. Sin eso, el patrón del
> IBAN se «tragaba» la palabra siguiente y la validación descartaba el IBAN
> entero.

### Capa 2 — Modelo de nombres

spaCy `es_core_news_lg` sobre CPU. Su salida se filtra con una lista de ruido
(etiquetas de plantilla, términos anatómicos, analitos…) y se recortan las
partículas de los bordes.

### Capa 3 — LLM local (opcional)

Se le exige devolver los fragmentos **literales**; luego se localizan por
posición exacta y **se descarta lo que el modelo se invente**. Salvaguardas: un
único sondeo de disponibilidad por documento (si el servidor no responde, se
salta y se avisa), presupuesto global de tiempo, y solo se admiten direcciones
de red privada.

### Solapamientos

`resolver_solapamientos()` en `motor.py`: gana la capa de menor número (regla
validada > modelo > IA). La detección perdedora **no se descarta entera**: se
recorta la parte solapada y se conserva el resto — perder texto sería una fuga.

---

## Historial de versiones

| Versión | Qué añadió |
|---|---|
| 0.1 | Web local, PDF con texto y Word, capas 1-2, perfiles, verificación y redacción destructiva |
| 0.2 | OCR de escaneados e imágenes, redacción de píxeles, detección de membretes |
| 0.3 | Capa 3 (LLM local) y diagnóstico de hardware |
| 0.4 | Informe de auditoría, segunda pasada, lotes por carpeta, métricas y modo portable |
| 0.5 | Desplazamiento consistente de fechas y rangos etarios |
| 0.6 | Revisión de calidad: correcciones de fugas, concurrencia y seguridad |
| 0.7 | **Universal**: perfiles jurídico, empresa, facturas y personal; IBAN, CIF, tarjetas, catastro, matrículas; identidad Nodo Local |
| 0.8 | **Bilingüe** español / inglés |

## Ideas pendientes

- Motor de detección para documentos **en inglés** (modelo NER inglés,
  identificadores SSN/NHS/NI, formato de fecha americano).
- Conversión automática de `.doc` antiguos en el servidor.
- Procesamiento en paralelo para lotes muy grandes.
- Sustituir por etiquetas («[PACIENTE]») en lugar de bloques negros.
