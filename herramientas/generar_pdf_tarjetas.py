"""Genera el PDF interactivo de las tarjetas digitales finales de ARAEMKA."""

from pathlib import Path
from PIL import Image
from reportlab.pdfgen import canvas


RAIZ = Path(__file__).resolve().parent.parent
TARJETAS = RAIZ / "materiales" / "tarjetas-whatsapp"
SALIDA = RAIZ / "output" / "pdf" / "ARAEMKA-tarjetas-digitales-interactivas.pdf"
IMAGENES = [
    "ARAEMKA-tarjeta-clara-anverso-es.png",
    "ARAEMKA-tarjeta-clara-reverso-en.png",
    "ARAEMKA-tarjeta-oscura-anverso-es.png",
    "ARAEMKA-tarjeta-oscura-reverso-en.png",
]


def main():
    SALIDA.parent.mkdir(parents=True, exist_ok=True)
    primera = Image.open(TARJETAS / IMAGENES[0])
    pdf = canvas.Canvas(str(SALIDA), pagesize=primera.size)
    pdf.setTitle("ARAEMKA - Tarjetas digitales interactivas")
    pdf.setSubject("ARAEMKA PDF y ARAEMKA Redact - enlaces oficiales")
    pdf.setAuthor("José Ramón Alberto Alonso")
    pdf.setCreator("ARAEMKA")

    for nombre in IMAGENES:
        ruta = TARJETAS / nombre
        with Image.open(ruta) as imagen:
            w, h = imagen.size
        pdf.setPageSize((w, h))
        pdf.drawImage(str(ruta), 0, 0, width=w, height=h)
        # El PDF conserva enlaces clicables aunque la tarjeta se comparta como imagen.
        pdf.linkURL("https://araemka.com", (0, 0, w, h), relative=0)
        if w == h:
            pdf.linkURL("mailto:contacto@araemka.com", (70, 300, 820, 430), relative=0)
        else:
            pdf.linkURL("mailto:contacto@araemka.com", (70, 100, 1050, 210), relative=0)
        pdf.showPage()
    pdf.save()
    print(SALIDA)


if __name__ == "__main__":
    main()
