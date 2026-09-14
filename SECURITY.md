# Seguridad de ARAEMKA Redact

## Versiones con soporte

Las correcciones de seguridad se aplican a la última versión publicada. Las
versiones anteriores deben considerarse sin soporte cuando exista una versión
posterior disponible.

## Comunicar una vulnerabilidad

Envía el informe de forma privada a **contacto@araemka.com**. Incluye la versión,
el sistema operativo, una descripción reproducible y el impacto posible. No
incluyas documentos reales, datos de pacientes, contraseñas ni otros secretos.

No abras una incidencia pública con detalles explotables antes de que exista
una corrección. Se acusará recibo y se coordinará una divulgación responsable.

## Modelo de seguridad

- El procesamiento normal se realiza localmente y los documentos permanecen en
  memoria durante un tiempo limitado.
- La capa de IA es opcional. Si se activa, recibe texto todavía no anonimizado y
  solo debe apuntar a Ollama o LM Studio en el propio equipo o en una red local
  de confianza.
- En un NAS, configura siempre una contraseña y publica el servicio únicamente
  en una red confiable o detrás de un proxy HTTPS correctamente administrado.
- Comprueba las sumas SHA-256 de los paquetes. Las sumas detectan alteraciones,
  pero no sustituyen la firma de código de Apple o Microsoft.
- ARAEMKA Redact ayuda a redactar datos; no certifica por sí solo la anonimización.
  Revisa íntegramente el resultado antes de compartirlo.

## Fuera de alcance

No se aceptan pruebas con datos personales reales, ataques de denegación de
servicio contra instalaciones ajenas ni acceso a sistemas sin autorización.

---

# ARAEMKA Redact security

Security fixes are applied to the latest release. Report vulnerabilities
privately to **contacto@araemka.com**, including the version, platform,
reproduction steps and likely impact. Never send real documents, patient data,
passwords or other secrets, and do not publish exploitable details before a fix
is available.

The optional local-AI layer receives text before redaction and must only use a
trusted Ollama or LM Studio endpoint on the local machine or private network.
Protect NAS deployments with a password and trusted network or an HTTPS reverse
proxy. Verify release SHA-256 checksums; they detect changes but do not replace
Apple or Microsoft code signing. Always review the final document: this tool
does not by itself certify anonymisation.
