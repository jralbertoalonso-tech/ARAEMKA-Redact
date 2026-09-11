# ARAEMKA Redact en tu Synology — instalación rápida

Esta carpeta contiene la aplicación **ya construida y probada**: el NAS no
necesita internet ni compilar nada.

```
anonipro-imagen.tar.gz   la aplicación y sus modelos locales (~2 GB)
docker-compose.yml       la configuración
```

## Antes de empezar

Abre `docker-compose.yml` y escribe una contraseña entre las comillas:

```yaml
ANONIPRO_PASSWORD: "la-que-tú-quieras"
```

## Cuatro pasos

1. **File Station** → copia esta carpeta dentro de la carpeta compartida
   **docker**.
2. **Container Manager → Imagen → Añadir → Añadir desde archivo** → elige
   `anonipro-imagen.tar.gz` y espera unos minutos.
3. **Container Manager → Proyecto → Crear**: nombre `anonipro`, ruta esta
   carpeta, «usar docker-compose.yml existente» → **Hecho**.
4. Entra desde cualquier navegador de la red: **http://IP-DE-TU-NAS:8080**

> Si sale un asistente pidiendo un «nombre de host», ciérralo: no hace falta.

## Actualizar

Detener el proyecto → borrar la imagen antigua → añadir la nueva desde archivo
→ iniciar el proyecto.

---

Guía completa (acceso desde fuera, conectar la IA local, resolución de
problemas): **docs/INSTALAR-EN-NAS.md** del proyecto.
