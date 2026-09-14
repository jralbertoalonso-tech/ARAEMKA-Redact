# ARAEMKA Redact — imagen Docker para Synology (Container Manager) y cualquier host con Docker.
# Todo el procesamiento es local; la imagen NO necesita internet una vez construida.

FROM python:3.12-slim

ARG ANONIPRO_VERSION=0.10.3
LABEL org.opencontainers.image.title="ARAEMKA Redact" \
      org.opencontainers.image.version="${ANONIPRO_VERSION}" \
      org.opencontainers.image.licenses="AGPL-3.0-only" \
      org.opencontainers.image.source="https://github.com/jralbertoalonso-tech/ARAEMKA-Redact"

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    ANONIPRO_PUERTO=8080

# OCR local (Fase 2): Tesseract + modelo español. Se instala del repositorio de
# Debian en tiempo de BUILD, así el contenedor funciona sin internet.
RUN apt-get update && apt-get install -y --no-install-recommends \
        tesseract-ocr tesseract-ocr-spa tesseract-ocr-eng \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 1) Dependencias de Python (capa cacheable)
COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r /app/backend/requirements.txt

# 2) Modelos NER (se descargan en tiempo de BUILD, no en ejecución, para que el
#    contenedor funcione sin internet). Grandes porque el NAS del usuario tiene
#    32 GB de RAM; cambia a _md o _sm si necesitas menos memoria.
#    - español: motor por defecto (siempre cargado).
#    - inglés: para documentos en inglés (Reino Unido y EE. UU.); se carga solo
#      si llega un documento en ese idioma.
RUN python -m spacy download es_core_news_lg && \
    python -m spacy download en_core_web_lg

# 3) Código de la aplicación
COPY backend /app/backend
COPY frontend /app/frontend
COPY LICENSE CODIGO-FUENTE.md THIRD-PARTY-NOTICES.md TRADEMARKS.md AVISO-LEGAL.md /app/

# La aplicación no necesita privilegios ni escribir fuera de /tmp.
RUN useradd --system --uid 10001 --home-dir /tmp --shell /usr/sbin/nologin araemka
USER 10001:10001

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=90s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/api/estado', timeout=3).read()"

# Un solo worker: el modelo NER se comparte en memoria y el estado (documentos
# en RAM) vive dentro del proceso. Para más concurrencia, ampliar en Fase 4.
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080", "--app-dir", "backend"]
