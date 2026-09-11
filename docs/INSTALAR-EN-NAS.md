# Instalar ARAEMKA Redact en un NAS Synology

Con ARAEMKA Redact en el NAS, **cualquier ordenador de la red lo usa desde el
navegador**, sin instalar nada en él. Es la mejor opción para una consulta, un
despacho o una oficina con equipos corporativos bloqueados.

Necesitas la carpeta técnica heredada **`AnoniPRO-synology`**, que se conserva
con ese nombre para poder actualizar instalaciones anteriores y contiene:

```
AnoniPRO-synology/
├─ anonipro-imagen.tar.gz   ← la aplicación ya preparada (~1,3 GB)
├─ docker-compose.yml       ← la configuración
└─ INSTRUCCIONES.md         ← la versión corta de este documento
```

La aplicación **ya viene construida y probada**: el NAS no necesita internet ni
compilar nada.

---

## Antes de empezar

- Instala **Container Manager** en el NAS (DSM → *Centro de paquetes*).
- **Elige una contraseña.** El NAS suele ser accesible por más gente, así que
  conviene protegerlo. Abre `docker-compose.yml` con cualquier editor de texto
  y escríbela entre las comillas:

  ```yaml
  ANONIPRO_PASSWORD: "la-que-tú-quieras"
  ```

---

## Paso 1 · Copiar la carpeta al NAS

Abre **File Station** y copia la carpeta `AnoniPRO-synology` dentro de la
carpeta compartida **docker** (si no existe: *Panel de control → Carpeta
compartida → Crear*).

## Paso 2 · Importar la aplicación

1. **Container Manager → Imagen → Añadir → Añadir desde archivo**.
2. Elige `docker/AnoniPRO-synology/anonipro-imagen.tar.gz`.
3. Espera a que aparezca **anonipro:latest** (tarda unos minutos: son 1,3 GB).

## Paso 3 · Crear el proyecto

1. **Container Manager → Proyecto → Crear**.
2. Rellena:
   - **Nombre:** `anonipro`
   - **Ruta:** la carpeta `docker/AnoniPRO-synology`
   - **Origen:** «Usar un docker-compose.yml existente» (lo detecta solo)
3. **Siguiente → Hecho**. Arranca en segundos.

> Si aparece un asistente pidiendo un **«nombre de host»**, es el portal web de
> Web Station: **ciérralo**, no hace falta.

## Paso 4 · Entrar

Desde cualquier navegador de la red:

```
http://IP-DE-TU-NAS:8080
```

La IP la ves en *DSM → Panel de control → Red*. Conviene fijarla como estática
para que no cambie, y guardar la dirección en favoritos.

---

## Actualizar a una versión nueva

1. Copia el `anonipro-imagen.tar.gz` nuevo encima del antiguo (File Station).
2. **Proyecto → anonipro → Detener**.
3. **Imagen →** elimina `anonipro:latest` **→ Añadir desde archivo** con el nuevo.
4. **Proyecto → anonipro → Iniciar**.

La interfaz se actualiza sola en el navegador: no hace falta vaciar la caché.

---

## Acceder desde fuera de casa

**No abras el puerto en el router ni uses QuickConnect** para este servicio.

La forma correcta y segura es una **red privada tipo Tailscale**: instálala en
el NAS y en tus dispositivos, y accede a `http://IP-DE-TAILSCALE:8080` desde
donde estés. El tráfico va cifrado de extremo a extremo entre tus propios
equipos, sin exponer nada a internet.

Ten en cuenta que, al usarlo desde fuera, el documento **sí viaja por internet**
(cifrado y solo entre tus equipos) hasta llegar al NAS, donde se procesa. En la
red local no sale de casa.

---

## Conectar la IA local (opcional)

El NAS ejecuta perfectamente las capas 1 y 2, pero **no debe ejecutar el modelo
de IA**: no tiene tarjeta gráfica y sería lentísimo. En su lugar puede
**delegarlo en otro equipo de tu red** (un Mac o un PC con Ollama):

1. En ese equipo, abre Ollama y activa **«Exponer a la red»** en sus ajustes.
2. En ARAEMKA Redact: **⚙️ Ajustes de IA** → dirección `http://IP-DEL-EQUIPO:11434` →
   elige el modelo → **Probar** → **Activar** → **Guardar**.

Ese equipo debe estar encendido para que la capa 3 funcione. Si se apaga,
ARAEMKA Redact lo detecta, sigue con las capas 1-2 y te avisa.

---

## Si algo falla

| Problema | Solución |
|---|---|
| «El puerto 8080 ya está en uso» | Edita `docker-compose.yml`: cambia `"8080:8080"` por `"8081:8080"` y entra por el 8081 |
| La página no carga | Container Manager → Contenedor → mira el **Registro**: al arrancar debe decir «Modelo NER listo» tras ~1 minuto |
| Pide una contraseña que no sabes | Es la de `ANONIPRO_PASSWORD` del `docker-compose.yml`, no la de DSM |

## Qué NO hace falta

- Internet en el NAS: no se descarga nada en marcha.
- Carpetas de datos: los documentos se procesan en memoria y nunca se escriben
  en el disco del NAS.
