# AnoniPRO — imagen Docker para Synology (Container Manager) y cualquier host con Docker.
# Todo el procesamiento es local; la imagen NO necesita internet una vez construida.

FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    ANONIPRO_PUERTO=8080

# OCR local (Fase 2): Tesseract + modelo español. Se instala del repositorio de
# Debian en tiempo de BUILD, así el contenedor funciona sin internet.
RUN apt-get update && apt-get install -y --no-install-recommends \
        tesseract-ocr tesseract-ocr-spa \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 1) Dependencias de Python (capa cacheable)
COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r /app/backend/requirements.txt

# 2) Modelo NER en español (se descarga en tiempo de BUILD, no en ejecución,
#    para que el contenedor funcione sin internet). Grande porque el NAS del
#    usuario tiene 32 GB de RAM; cambia a _md o _sm si necesitas menos memoria.
RUN python -m spacy download es_core_news_lg

# 3) Código de la aplicación
COPY backend /app/backend
COPY frontend /app/frontend

EXPOSE 8080

# Un solo worker: el modelo NER se comparte en memoria y el estado (documentos
# en RAM) vive dentro del proceso. Para más concurrencia, ampliar en Fase 4.
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080", "--app-dir", "backend"]
