# Instalar AnoniPRO en el Synology DS923+ — paso a paso

Esta carpeta contiene todo lo necesario. La imagen ya viene **construida y
probada**: el NAS no necesita internet ni compilar nada.

```
AnoniPRO-synology/
├─ anonipro-imagen.tar.gz   ← la aplicación empaquetada (imagen Docker)
├─ docker-compose.yml       ← la configuración (puerto, contraseña…)
└─ INSTRUCCIONES.md         ← este documento
```

## Antes de empezar (1 minuto)

- Ten instalado **Container Manager** en el NAS (DSM → Centro de paquetes →
  busca «Container Manager» → Instalar). Si ya lo tienes, sigue.
- **Contraseña de la web (recomendada):** abre `docker-compose.yml` con
  cualquier editor y escribe una contraseña entre las comillas de
  `ANONIPRO_PASSWORD: ""`. Puedes hacerlo también después, desde DSM
  (Container Manager → Proyecto → anonipro → Editar).

## Paso 1 — Copiar esta carpeta al NAS

1. Abre **File Station** en DSM.
2. En la carpeta compartida **docker** (si no existe, créala: Panel de
   control → Carpeta compartida → Crear), copia la carpeta entera
   `AnoniPRO-synology`. Puedes arrastrarla desde el Mac a File Station.

## Paso 2 — Importar la imagen

1. Abre **Container Manager** → pestaña **Imagen** → botón **Añadir** →
   **Añadir desde archivo**.
2. Elige `docker/AnoniPRO-synology/anonipro-imagen.tar.gz` y acepta.
3. Espera a que aparezca la imagen **anonipro:latest** en la lista
   (tarda unos minutos: son ~2 GB).

## Paso 3 — Crear el proyecto

1. Container Manager → pestaña **Proyecto** → **Crear**.
2. Rellena:
   - **Nombre del proyecto:** `anonipro`
   - **Ruta:** selecciona la carpeta `docker/AnoniPRO-synology`
   - **Origen:** «Usar un docker-compose.yml existente» (lo detecta solo).
3. **Siguiente** → **Hecho**. En unos segundos el proyecto quedará
   **en ejecución** (no compila nada: usa la imagen del paso 2).

## Paso 4 — Probar

Desde cualquier navegador de tu red local (tu Mac, un PC del trabajo si está
en la misma red, el móvil por wifi):

```
http://IP-DE-TU-NAS:8080
```

La IP del NAS la ves en DSM → Panel de control → Red → Interfaz de red
(algo como 192.168.1.XX). Consejo: en DSM puedes fijarla como IP estática
para que no cambie, y así guardar la dirección en favoritos.

Sube un documento de prueba y comprueba que detecta y redacta.

## Problemas típicos

- **«El puerto 8080 ya está en uso»** al crear el proyecto: otro paquete del
  NAS lo ocupa. Edita `docker-compose.yml` y cambia `"8080:8080"` por
  `"8081:8080"`; accederás por `http://IP:8081`.
- **No carga la página**: comprueba en Container Manager → Contenedor que
  `anonipro` está en ejecución, y mira su pestaña **Registro** (log): al
  arrancar debe decir «Modelo NER listo: es_core_news_lg» tras ~1 minuto.
- **Pide contraseña y no la sabes**: es la de `ANONIPRO_PASSWORD` del
  docker-compose.yml (no es la de DSM). Edítala y reinicia el proyecto.

## Actualizar a una versión nueva

Cuando haya una imagen nueva (`anonipro-imagen.tar.gz` regenerado):
1. Copia el tar.gz nuevo encima del antiguo en File Station.
2. Container Manager → Proyecto → anonipro → **Detener**.
3. Imagen → elimina `anonipro:latest` → **Añadir desde archivo** con el nuevo.
4. Proyecto → anonipro → **Iniciar**.

## Qué NO hace falta

- Internet en el NAS: nada se descarga en ejecución.
- Volúmenes ni carpetas de datos: los documentos se procesan solo en la
  memoria RAM del contenedor y se borran solos.
- Abrir puertos al exterior: NO expongas el 8080 fuera de tu red local
  (ni QuickConnect ni reenvío de puertos del router para este servicio).
