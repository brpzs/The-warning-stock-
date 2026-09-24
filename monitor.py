import os
import requests
from bs4 import BeautifulSoup

# Traer la URL secreta de Discord
DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK")

BASE_URL = "https://thewarningband.com"

# Vinilos con sus URLs fijas
VINILOS = [
    {
        "nombre": "Queen of the Murder Scene (Vinilo)",
        "url": f"{BASE_URL}/products/queen-of-the-murder-scene-vinyl"
    },
    {
        "nombre": "XXI Century Blood (Vinilo)",
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

def verificar_estado():
    reporte = ["📊 **ESTADO DE STOCK (The Warning)**\n"]
    
    # 1. Revisar Vinilos
    for prod in VINILOS:
        try:
            res = requests.get(prod["url"], headers=headers, timeout=10)
            if res.status_code == 200:
                soup = BeautifulSoup(res.text, "html.parser")
                texto = soup.get_text().lower()
                boton_agregar = soup.find("button", {"name": "add"})
                esta_agotado = "sold out" in texto or "agotado" in texto
                
                if boton_agregar and not esta_agotado:
                    reporte.append(f"🟢 **[{prod['nombre']}]({prod['url']})**: ¡DISPONIBLE! 🛒")
                else:
                    reporte.append(f"🔴 **[{prod['nombre']}]({prod['url']})**: Agotado")
            else:
                reporte.append(f"🔴 **[{prod['nombre']}]({prod['url']})**: Página no activa / No disponible")
        except Exception as e:
            reporte.append(f"⚠️ Error revisando {prod['nombre']}: {e}")

    # 2. Revisar la sección de música buscando CDs PUBLICADOS
    try:
        url_musica = f"{BASE_URL}/collections/music"
        res = requests.get(url_musica, headers=headers, timeout=10)
        soup = BeautifulSoup(res.text, "html.parser")
        
        # Buscar enlaces directos a productos
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
