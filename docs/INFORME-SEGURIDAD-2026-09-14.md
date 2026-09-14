# Revisión de seguridad de ARAEMKA Redact

Fecha: 14 de septiembre de 2026  
Base revisada: versión 0.10.2, commit `e997143`

## Alcance y método

Revisión manual del backend, frontend, contenedor y flujos de construcción;
ejecución de la batería funcional; análisis estático de Python; y auditoría de
las dependencias declaradas. No es una auditoría externa ni una certificación.

## Hallazgos principales

### Alta — redirección de la IA local

La dirección inicial de Ollama/LM Studio se comprobaba como privada, pero el
cliente HTTP seguía redirecciones. Un servicio local malicioso o comprometido
podía redirigir una petición a Internet y sacar texto sin anonimizar.

**Corrección preparada:** validar esquema, credenciales, ruta y todas las IP
resueltas antes de cada petición; desactivar proxies y redirecciones; limitar el
tamaño de respuesta y el tiempo máximo; y añadir pruebas de regresión.

### Media — transporte HTTP en el NAS

El servicio del NAS se usa actualmente por HTTP dentro de la LAN. La contraseña
y los documentos viajan sin cifrado frente a otros equipos capaces de observar
esa red.

**Pendiente operativo:** publicar ARAEMKA detrás del proxy inverso HTTPS de DSM,
activar `ANONIPRO_COOKIE_SECURE=true` y restringir el puerto 8080 a la red o al
proxy que corresponda. No exponerlo directamente a Internet.

### Media — registro operativo publicado

El repositorio contenía `docs/ACCESO-CODEX.md`, un registro que debe permanecer
privado aunque no incluya contraseñas.

**Corrección preparada:** retirarlo del control de versiones, ignorarlo y dejar
en `AGENTS.md` únicamente la norma genérica de no publicarlo.

### Media — agotamiento de recursos

Los archivos admitidos pueden expandirse y procesarse completamente en memoria;
además, el almacén no fija un máximo global de documentos concurrentes. En una
red compartida, cargas simultáneas podrían agotar RAM o CPU.

**Mitigación preparada:** límites de memoria y procesos en Docker. **Pendiente de
producto:** cuota global de RAM y límite explícito de trabajos pesados.

### Baja — endurecimiento web y contenedor

Faltaban cabeceras defensivas, la cookie usaba `SameSite=Lax` y el contenedor se
ejecutaba como root.

**Corrección preparada:** `no-store` para la API, CSP y otras cabeceras; cookie
`SameSite=Strict` con opción `Secure`; usuario sin privilegios, capacidades
eliminadas, `no-new-privileges` y comprobación de salud.

## Evidencia de pruebas

- Batería funcional y de privacidad: 103 pruebas superadas.
- Compilación sintáctica Python y validación sintáctica JavaScript: correctas.
- Dependencias resueltas el 14/09/2026: ninguna vulnerabilidad conocida según
  `pip-audit`. Es una fotografía temporal, no una garantía futura.
- Análisis estático final: ningún hallazgo de severidad media o alta; los avisos
  restantes son de severidad baja.
- La publicación solo debe hacerse después de repetir estas pruebas sobre el
  árbol final y revisar los resultados de dependencias y análisis estático.

## Riesgo residual y prioridad

Antes de considerar una instalación institucional, faltan HTTPS en el NAS,
firma/notarización de los ejecutables, límites de concurrencia y una revisión
externa independiente con documentos ficticios. La prioridad inmediata es
publicar la corrección de la capa 3 y retirar el registro operativo público.
