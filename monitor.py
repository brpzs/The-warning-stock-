import os
import requests
from bs4 import BeautifulSoup

# Configuración del Webhook guardado en GitHub Secrets
DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK")

# Lista de productos a rastrear
PRODUCTOS = [
    {
        "nombre": "Queen of the Murder Scene (Vinilo)",
        "url": "https://thewarningband.com/products/queen-of-the-murder-scene-vinyl"
    },
    {
        "nombre": "XXI Century Blood (Vinilo)",
        "url": "https://thewarningband.com/products/century-blood-vinyl"
    },
    {
        "nombre": "Colección completa de Música (Buscar CDs/Re-stock)",
        "url": "https://thewarningband.com/collections/music"
    }
]

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
}

def enviar_discord(mensaje):
    """Envia mensaje al canal de Discord usando el Webhook"""
    if DISCORD_WEBHOOK_URL:
        payload = {"content": mensaje}
        requests.post(DISCORD_WEBHOOK_URL, json=payload)
    else:
        print("Error: No se encontró la URL del Webhook de Discord.")

def revisar_vinilo(producto):
    """Revisa las páginas individuales de los vinilos"""
    try:
        res = requests.get(producto["url"], headers=headers, timeout=10)
        soup = BeautifulSoup(res.text, "html.parser")
        
        # En la tienda de The Warning, cuando no hay stock aparece la leyenda 'Sold out' o 'Agotado'
        # Si NO dice 'Sold out', significa que habilitaron la compra / stock.
        texto_pagina = soup.get_text().lower()
        
        # Verificamos si existe el botón habilitado de "Add to cart"
        boton_agregar = soup.find("button", {"name": "add"})
        esta_agotado = "sold out" in texto_pagina or "agotado" in texto_pagina

        if boton_agregar and not esta_agotado:
            enviar_discord(f"🚨 **¡STOCK DETECTADO!** 🚨\n**{producto['nombre']}** ya está disponible.\nComprar aquí: {producto['url']}")
    except Exception as e:
        print(f"Error revisando {producto['nombre']}: {e}")

def revisar_coleccion():
    """Revisa si aparecen versiones en CD o ítems nuevos en la sección de música"""
    try:
        url_coleccion = "https://thewarningband.com/collections/music"
        res = requests.get(url_coleccion, headers=headers, timeout=10)
        soup = BeautifulSoup(res.text, "html.parser")
        
        texto_pagina = soup.get_text().lower()
        
        # Alertas específicas si detecta un CD de alguno de estos dos álbumes
        if "queen of the murder scene" in texto_pagina and "cd" in texto_pagina:
            enviar_discord(f"💿 **¡Posible CD detectado!** Se encontró mención de 'Queen of the Murder Scene CD' en la tienda: {url_coleccion}")
            
        if ("xxi century blood" in texto_pagina or "21st century blood" in texto_pagina) and "cd" in texto_pagina:
            enviar_discord(f"💿 **¡Posible CD detectado!** Se encontró mención de 'XXI Century Blood CD' en la tienda: {url_coleccion}")
            
    except Exception as e:
        print(f"Error revisando la colección de música: {e}")

if __name__ == "__main__":
    # 1. Revisar vinilos específicos
    for prod in PRODUCTOS[:2]:
        revisar_vinilo(prod)
        
    # 2. Revisar si publicaron CDs en la sección general de música
    revisar_coleccion()
