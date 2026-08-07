#!/bin/bash
# Verifica el sello de tiempo de la prueba de autoría de AnoniPRO.
# Uso:  bash verificar.sh   (desde la carpeta prueba-autoria)
cd "$(dirname "$0")"

echo "── Verificación del sello de tiempo — AnoniPRO ──"
echo
echo "Fecha certificada por la autoridad:"
openssl ts -reply -in huella.tsr -text 2>/dev/null | grep -i "Time stamp:" | sed 's/^/  /'
echo
echo "Resultado de la verificación:"
openssl ts -verify -data HUELLA.txt -in huella.tsr \
  -CAfile freetsa-cacert.pem -untrusted freetsa-tsa.crt 2>&1 | grep -i "Verification" | sed 's/^/  /'
echo
echo "(Si dice 'Verification: OK', el sello es válido y la fecha es auténtica.)"
