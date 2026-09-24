import os
import requests
from bs4 import BeautifulSoup

# Configuración
URL_PRODUCTO = "https://ejemplo.com/pagina-de-tu-producto"
DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK")

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

def comprobar_stock():
    respuesta = requests.get(URL_PRODUCTO, headers=headers)
    soup = BeautifulSoup(respuesta.text, "html.parser")

    # AQUÍ ADAPTAS LA BÚSQUEDA:
    # Ejemplo: si la página tiene un botón "Añadir al carrito", lo buscamos
    boton_comprar = soup.find("button", {"id": "add-to-cart"}) 

    if boton_comprar:
        notificar_discord("¡Hay stock disponible! Enlace: " + URL_PRODUCTO)

def notificar_discord(mensaje):
    payload = {"content": mensaje}
    requests.post(DISCORD_WEBHOOK_URL, json=payload)

if __name__ == "__main__":
    comprobar_stock()
