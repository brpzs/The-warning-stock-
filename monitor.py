import os
import requests
from bs4 import BeautifulSoup

# Traer la URL secreta de Discord
DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK")

BASE_URL = "https://thewarningband.com"

# Tasa de cambio estimada para la conversión (USD -> ARS)
# Modifica este valor según la cotización que prefieras (ej. Tarjeta/MEP)
TIPO_DE_CAMBIO_ARS = 1520.00

# Vinilos con sus nombres de producto en Shopify
VINILOS = [
    {
        "nombre": "Queen of the Murder Scene (Vinilo)",
        "handle": "queen-of-the-murder-scene-vinyl",
        "url": f"{BASE_URL}/products/queen-of-the-murder-scene-vinyl"
    },
    {
        "nombre": "XXI Century Blood (Vinilo)",
        "handle": "century-blood-vinyl",
        "url": f"{BASE_URL}/products/century-blood-vinyl"
    }
]

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def enviar_discord(mensaje):
    if DISCORD_WEBHOOK_URL:
        payload = {"content": mensaje}
        requests.post(DISCORD_WEBHOOK_URL, json=payload)

def obtener_datos_producto_shopify(handle):
    """Consulta los datos JSON nativos del producto en Shopify"""
    try:
        url_json = f"{BASE_URL}/products/{handle}.json"
        res = requests.get(url_json, headers=headers, timeout=10)
        if res.status_code == 200:
            datos = res.json().get("product", {})
            variantes = datos.get("variants", [])
            if variantes:
                precio_usd = float(variantes[0].get("price", 0))
                disponible = any(v.get("available", False) for v in variantes)
                return disponible, precio_usd
    except Exception as e:
        print(f"Error extrayendo datos JSON de {handle}: {e}")
    return False, 0.0

def formatear_precio(precio_usd):
    if precio_usd > 0:
        precio_ars = precio_usd * TIPO_DE_CAMBIO_ARS
        return f"💵 **${precio_usd:.2f} USD** *(~${precio_ars:,.0f} ARS)*"
    return "Precio N/A"

def verificar_estado():
    reporte = ["📊 **ESTADO DE STOCK Y PRECIOS (The Warning)**\n"]
    
    # 1. Revisar Vinilos
    for prod in VINILOS:
        disponible, precio_usd = obtener_datos_producto_shopify(prod["handle"])
        info_precio = formatear_precio(precio_usd)
        
        if disponible:
            reporte.append(f"🟢 **[{prod['nombre']}]({prod['url']})**: ¡DISPONIBLE! 🛒\n   └ Precio: {info_precio}")
        else:
            reporte.append(f"🔴 **[{prod['nombre']}]({prod['url']})**: Agotado\n   └ Precio: {info_precio}")

    # 2. Revisar la sección de música buscando CDs PUBLICADOS
    try:
        url_musica = f"{BASE_URL}/collections/music"
        res = requests.get(url_musica, headers=headers, timeout=10)
        soup = BeautifulSoup(res.text, "html.parser")
        
        enlaces_productos = soup.find_all("a", href=True)
        
        url_cd_qotms = None
        url_cd_xxicb = None

        for a in enlaces_productos:
            href = a['href']
            href_lower = href.lower()
            if "/products/" in href_lower:
                if "queen" in href_lower and "cd" in href_lower:
                    url_cd_qotms = href if href.startswith("http") else f"{BASE_URL}{href}"
                if ("century" in href_lower or "xxicb" in href_lower) and "cd" in href_lower:
                    url_cd_xxicb = href if href.startswith("http") else f"{BASE_URL}{href}"

        # Reporte QOTMS CD
        if url_cd_qotms:
            reporte.append(f"🟢 **[Queen of the Murder Scene (CD)]({url_cd_qotms})**: ¡DISPONIBLE!")
        else:
            reporte.append(f"🔴 **[Queen of the Murder Scene (CD)]({url_musica})**: No disponible")

        # Reporte XXI Century Blood CD
        if url_cd_xxicb:
            reporte.append(f"🟢 **[XXI Century Blood (CD)]({url_cd_xxicb})**: ¡DISPONIBLE!")
        else:
            reporte.append(f"🔴 **[XXI Century Blood (CD)]({url_musica})**: No disponible")

    except Exception as e:
        reporte.append(f"⚠️ Error al revisar el catálogo de CDs: {e}")

    # Enviar reporte consolidado a Discord
    enviar_discord("\n".join(reporte))

if __name__ == "__main__":
    verificar_estado()
