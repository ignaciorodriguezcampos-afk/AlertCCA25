import os
import json
import hashlib
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from datetime import datetime
from pathlib import Path

URL = "https://www.ccuentas.es/proceso-selectivo/auditores-2025-4452"
ARCHIVO = Path("enlaces_detectados.json")

TOPIC = os.environ.get("NTFY_TOPIC", "").strip()
NTFY_URL = "https://ntfy.sh/" + TOPIC

def obtener_enlaces():
    respuesta = requests.get(
        URL,
        timeout=30,
        headers={"User-Agent": "Mozilla/5.0"}
    )
    respuesta.raise_for_status()

    soup = BeautifulSoup(respuesta.text, "html.parser")
    enlaces = {}

    for enlace in soup.find_all("a", href=True):
        titulo = enlace.get_text(" ", strip=True)
        destino = urljoin(URL, enlace["href"])

        if not titulo:
            continue

        if destino.startswith("http"):
            identificador = hashlib.sha256(
                destino.encode("utf-8")
            ).hexdigest()

            enlaces[identificador] = {
                "titulo": titulo,
                "url": destino
            }

    return enlaces


def notificar(novedades):
    if not TOPIC:
        raise RuntimeError("Falta configurar NTFY_TOPIC")

    for enlace in novedades:
        mensaje = (
            "Nueva publicacion en Auditores 2025\n\n"
            + enlace["titulo"]
            + "\n\n"
            + enlace["url"]
        )

        respuesta = requests.post(
            NTFY_URL,
            data=mensaje.encode("utf-8"),
            headers={
                "Title": "CAMARA DE CUENTAS - NUEVA PUBLICACION",
                "Priority": "high",
                "Tags": "bell"
            },
            timeout=30
        )
        respuesta.raise_for_status()


def main():
    print("Comprobando publicaciones...")
    actuales = obtener_enlaces()

    if ARCHIVO.exists():
        anteriores = json.loads(
            ARCHIVO.read_text(encoding="utf-8")
        )
    else:
        anteriores = None

    if anteriores is None:
        print("Primera comprobacion: creando referencia inicial.")
    else:
        novedades = [
            enlace
            for identificador, enlace in actuales.items()
            if identificador not in anteriores
        ]

        if novedades:
            print(f"Detectadas {len(novedades)} novedades.")
            notificar(novedades)
        else:
            print("Sin nuevas publicaciones.")

    ARCHIVO.write_text(
        json.dumps(actuales, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    print("Comprobacion finalizada:", datetime.now())


if __name__ == "__main__":
    main()
