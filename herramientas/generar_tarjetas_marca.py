"""Genera las tarjetas digitales finales de ARAEMKA desde el logo maestro."""

from pathlib import Path
from PIL import Image, ImageDraw, ImageFont


RAIZ = Path(__file__).resolve().parent.parent
MARCA = RAIZ / "materiales" / "marca" / "definitivo"
SALIDA = RAIZ / "materiales" / "tarjetas-whatsapp"
FUENTE = Path("/System/Library/Fonts/Supplemental/Arial.ttf")
FUENTE_NEGRITA = Path("/System/Library/Fonts/Supplemental/Arial Bold.ttf")


def fuente(tamano: int, negrita: bool = False):
    return ImageFont.truetype(str(FUENTE_NEGRITA if negrita else FUENTE), tamano)


def ajustar(imagen: Image.Image, ancho: int, alto: int) -> Image.Image:
    copia = imagen.copy()
    copia.thumbnail((ancho, alto), Image.Resampling.LANCZOS)
    return copia


def degradado(tamano, superior, inferior):
    ancho, alto = tamano
    lienzo = Image.new("RGB", tamano)
    px = lienzo.load()
    for y in range(alto):
        t = y / max(alto - 1, 1)
        color = tuple(round(a * (1 - t) + b * t) for a, b in zip(superior, inferior))
        for x in range(ancho):
            px[x, y] = color
    return lienzo.convert("RGBA")


def fondo_nodos(lienzo: Image.Image, oscuro: bool):
    capa = Image.new("RGBA", lienzo.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(capa)
    w, h = lienzo.size
    color = (28, 150, 224, 22 if oscuro else 14)
    puntos = [(50, 75), (220, 210), (w - 210, 90), (w - 80, 265), (180, h - 80)]
    for a, b in zip(puntos, puntos[1:]):
        d.line([a, b], fill=color, width=max(3, w // 420))
    r = max(13, w // 95)
    for x, y in puntos:
        d.ellipse((x-r, y-r, x+r, y+r), fill=color)
    lienzo.alpha_composite(capa)


def pegar_centrado(lienzo, imagen, y):
    x = (lienzo.width - imagen.width) // 2
    lienzo.alpha_composite(imagen, (x, y))


def tarjeta_cuadrada(idioma: str):
    es = idioma == "es"
    lienzo = degradado((1254, 1254), (255, 255, 255), (236, 247, 253))
    fondo_nodos(lienzo, oscuro=False)
    d = ImageDraw.Draw(lienzo)

    logo = ajustar(Image.open(MARCA / "ARAEMKA-logo-definitivo-transparente.png").convert("RGBA"), 1060, 275)
    pegar_centrado(lienzo, logo, 70)

    azul = (4, 43, 88, 255)
    cyan = (0, 177, 236, 255)
    suave = (52, 93, 128, 255)
    centro = lienzo.width // 2
    subtitulo = "Herramientas locales para documentos" if es else "Local document tools"
    caja = d.textbbox((0, 0), subtitulo, font=fuente(48))
    d.text((centro - (caja[2] - caja[0]) / 2, 360), subtitulo, font=fuente(48), fill=suave)
    productos = "ARAEMKA PDF  •  ARAEMKA Redact"
    caja = d.textbbox((0, 0), productos, font=fuente(53, True))
    d.text((centro - (caja[2] - caja[0]) / 2, 438), productos, font=fuente(53, True), fill=azul)

    d.rounded_rectangle((80, 540, 1174, 690), radius=36, fill=(218, 239, 250, 245), outline=(163, 216, 242, 255), width=3)
    d.ellipse((116, 577, 194, 655), fill=(4, 76, 139, 255))
    d.arc((139, 593, 171, 625), 180, 360, fill="white", width=5)
    d.rounded_rectangle((137, 608, 173, 638), radius=5, outline="white", width=5)
    privacidad = "Tus documentos no salen de tu equipo" if es else "Your documents never leave your device"
    d.text((225, 585), privacidad, font=fuente(43, True), fill=azul)

    etiqueta = "PRIVACIDAD LOCAL" if es else "LOCAL PRIVACY"
    d.text((94, 750), etiqueta, font=fuente(23, True), fill=cyan)
    d.text((94, 804), "araemka.com", font=fuente(49, True), fill=azul)
    d.text((94, 880), "contacto@araemka.com", font=fuente(43, True), fill=azul)
    d.text((94, 968), "José Ramón Alberto Alonso", font=fuente(37), fill=suave)

    qr = ajustar(Image.open(SALIDA / "ARAEMKA-qr-web.png").convert("RGBA"), 280, 280)
    d.rounded_rectangle((850, 754, 1174, 1127), radius=28, fill="white", outline=(0, 139, 210, 255), width=4)
    lienzo.alpha_composite(qr, (872, 780))
    pie = "Escanea · araemka.com" if es else "Scan · araemka.com"
    caja = d.textbbox((0, 0), pie, font=fuente(24, True))
    d.text((1012 - (caja[2] - caja[0]) / 2, 1080), pie, font=fuente(24, True), fill=azul)
    return lienzo.convert("RGB")


def tarjeta_apaisada(idioma: str):
    es = idioma == "es"
    lienzo = degradado((1672, 941), (2, 42, 78), (1, 20, 42))
    fondo_nodos(lienzo, oscuro=True)
    d = ImageDraw.Draw(lienzo)

    logo = ajustar(Image.open(MARCA / "ARAEMKA-logo-definitivo-negativo.png").convert("RGBA"), 1180, 300)
    lienzo.alpha_composite(logo, (72, 55))
    blanco = (244, 250, 255, 255)
    cyan = (107, 214, 255, 255)
    dorado = (255, 174, 66, 255)

    subtitulo = "Herramientas locales para documentos" if es else "Local document tools"
    d.text((96, 335), subtitulo, font=fuente(47), fill=cyan)
    d.text((96, 418), "ARAEMKA PDF  •  ARAEMKA Redact", font=fuente(49, True), fill=blanco)
    d.rounded_rectangle((82, 515, 1590, 635), radius=34, fill=(5, 69, 114, 230), outline=(21, 166, 225, 255), width=3)
    privacidad = "Tus documentos no salen de tu equipo" if es else "Your documents never leave your device"
    d.text((128, 548), privacidad, font=fuente(43, True), fill=dorado)

    d.text((96, 700), "araemka.com", font=fuente(43, True), fill=blanco)
    d.text((96, 768), "contacto@araemka.com", font=fuente(40, True), fill=blanco)
    d.text((96, 838), "José Ramón Alberto Alonso", font=fuente(34), fill=cyan)

    qr = ajustar(Image.open(SALIDA / "ARAEMKA-qr-web.png").convert("RGBA"), 230, 230)
    d.rounded_rectangle((1260, 667, 1565, 912), radius=24, fill="white", outline=(62, 193, 245, 255), width=4)
    lienzo.alpha_composite(qr, (1297, 675))
    return lienzo.convert("RGB")


def main():
    SALIDA.mkdir(parents=True, exist_ok=True)
    salidas = {
        "ARAEMKA-tarjeta-clara-anverso-es.png": tarjeta_cuadrada("es"),
        "ARAEMKA-tarjeta-clara-reverso-en.png": tarjeta_cuadrada("en"),
        "ARAEMKA-tarjeta-oscura-anverso-es.png": tarjeta_apaisada("es"),
        "ARAEMKA-tarjeta-oscura-reverso-en.png": tarjeta_apaisada("en"),
    }
    for nombre, imagen in salidas.items():
        imagen.save(SALIDA / nombre, format="PNG", optimize=True)
        print(SALIDA / nombre)


if __name__ == "__main__":
    main()
