import os
import requests
from bs4 import BeautifulSoup

# Configuración del Webhook guardado en GitHub Secrets
DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK")

PRODUCTOS = [
    {
        "nombre": "Queen of the Murder Scene (Vinilo)",
        "url": "https://thewarningband.com/products/queen-of-the-murder-scene-vinyl"
    },
    {
        "nombre": "XXI Century Blood (Vinilo)",
        "url": "https://thewarningband.com/products/century-blood-vinyl"
    }
]

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
}

def enviar_discord(mensaje):
    """Envía mensaje al canal de Discord usando el Webhook"""
    if DISCORD_WEBHOOK_URL:
        payload = {"content": mensaje}
        requests.post(DISCORD_WEBHOOK_URL, json=payload)
    else:
        print("Error: No se encontró la URL del Webhook de Discord.")

def verificar_estado():
    reporte = ["📊 **REPORTE DE STOCK ACTUAL (The Warning)**\n"]
    
    # 1. Revisar Vinilos
    for prod in PRODUCTOS:
        try:
            res = requests.get(prod["url"], headers=headers, timeout=10)
            soup = BeautifulSoup(res.text, "html.parser")
            
            texto = soup.get_text().lower()
            boton_agregar = soup.find("button", {"name": "add"})
            esta_agotado = "sold out" in texto or "agotado" in texto
            
            if boton_agregar and not esta_agotado:
                reporte.append(f"✅ **{prod['nombre']}**: ¡CON STOCK! 🟢\nEnlace: {prod['url']}")
            else:
                reporte.append(f"❌ **{prod['nombre']}**: Agotado 🔴")
        except Exception as e:
            reporte.append(f"⚠️ Error revisando {prod['nombre']}: {e}")

    # 2. Revisar si hay CDs en la tienda
    try:
        url_coleccion = "https://thewarningband.com/collections/music"
        res = requests.get(url_coleccion, headers=headers, timeout=10)
        soup = BeautifulSoup(res.text, "html.parser")
        texto = soup.get_text().lower()

        cd_qotms = "queen of the murder scene" in texto and "cd" in texto
        cd_xxicb = ("xxi century blood" in texto or "21st century blood" in texto) and "cd" in texto

        if cd_qotms:
            reporte.append("✅ **Queen of the Murder Scene (CD)**: ¡Detectado en la tienda! 🟢")
        else:
            reporte.append("❌ **Queen of the Murder Scene (CD)**: No disponible 🔴")

        if cd_xxicb:
            reporte.append("✅ **XXI Century Blood (CD)**: ¡Detectado en la tienda! 🟢")
        else:
            reporte.append("❌ **XXI Century Blood (CD)**: No disponible 🔴")

    except Exception as e:
        reporte.append(f"⚠️ Error revisando catálogo de CDs: {e}")

    # Enviar reporte consolidado a Discord
    enviar_discord("\n".join(reporte))

if __name__ == "__main__":
    verificar_estado()
