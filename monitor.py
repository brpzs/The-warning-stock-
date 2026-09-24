import os
import json
import requests
from bs4 import BeautifulSoup

# Traer la URL secreta de Discord desde Secrets
DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK")

BASE_URL = "https://thewarningband.com"
ARCHIVO_ESTADO = "estado.json"

# Tasa de cambio estimada (USD -> ARS)
TIPO_DE_CAMBIO_ARS = 1520.00

VINILOS = [
    {
        "id": "qotms_vinyl",
        "nombre": "Queen of the Murder Scene (Vinilo)",
        "handle": "queen-of-the-murder-scene-vinyl",
        "url": f"{BASE_URL}/products/queen-of-the-murder-scene-vinyl"
    },
    {
        "id": "xxicb_vinyl",
        "nombre": "XXI Century Blood (Vinilo)",
        "handle": "century-blood-vinyl",
        "url": f"{BASE_URL}/products/century-blood-vinyl"
    }
]

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def cargar_estado_anterior():
    if os.path.exists(ARCHIVO_ESTADO):
        try:
            with open(ARCHIVO_ESTADO, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def guardar_estado_actual(estado):
    with open(ARCHIVO_ESTADO, "w", encoding="utf-8") as f:
        json.dump(estado, f, indent=4, ensure_ascii=False)

def enviar_discord(mensaje):
    if DISCORD_WEBHOOK_URL:
        payload = {"content": mensaje}
        requests.post(DISCORD_WEBHOOK_URL, json=payload)

def obtener_datos_producto_shopify(handle):
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
    estado_anterior = cargar_estado_anterior()
    estado_actual = {}
    cambios_detectados = []

    # 1. Revisar Vinilos
    for prod in VINILOS:
        disponible, precio_usd = obtener_datos_producto_shopify(prod["handle"])
        estado_actual[prod["id"]] = disponible
        info_precio = formatear_precio(precio_usd)
        
        # Comparar con el estado anterior
        estaba_disponible = estado_anterior.get(prod["id"], None)
        
        if estaba_disponible != disponible:
            if disponible:
                cambios_detectados.append(
                    f"🟢 **CAMBIO DE ESTADO:** ¡AHORA HAY STOCK! 🛒\n"
                    f"👉 **[{prod['nombre']}]({prod['url']})**\n"
                    f"   └ Precio: {info_precio}"
                )
            elif estaba_disponible is not None:
                cambios_detectados.append(
                    f"🔴 **CAMBIO DE ESTADO:** Se agotó el stock.\n"
                    f"👉 **[{prod['nombre']}]({prod['url']})**"
                )

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

        # CD QOTMS
        qotms_cd_disponible = url_cd_qotms is not None
        estado_actual["qotms_cd"] = qotms_cd_disponible
        if estado_anterior.get("qotms_cd", None) != qotms_cd_disponible:
            if qotms_cd_disponible:
                cambios_detectados.append(f"🟢 **CAMBIO DE ESTADO:** ¡CD PUBLICADO!\n👉 **[Queen of the Murder Scene (CD)]({url_cd_qotms})**")
            elif estado_anterior.get("qotms_cd") is not None:
                cambios_detectados.append(f"🔴 **CAMBIO DE ESTADO:** CD retirado o agotado.\n👉 **[Queen of the Murder Scene (CD)]({url_musica})**")

        # CD XXI Century Blood
        xxicb_cd_disponible = url_cd_xxicb is not None
        estado_actual["xxicb_cd"] = xxicb_cd_disponible
        if estado_anterior.get("xxicb_cd", None) != xxicb_cd_disponible:
            if xxicb_cd_disponible:
                cambios_detectados.append(f"🟢 **CAMBIO DE ESTADO:** ¡CD PUBLICADO!\n👉 **[XXI Century Blood (CD)]({url_cd_xxicb})**")
            elif estado_anterior.get("xxicb_cd") is not None:
                cambios_detectados.append(f"🔴 **CAMBIO DE ESTADO:** CD retirado o agotado.\n👉 **[XXI Century Blood (CD)]({url_musica})**")

    except Exception as e:
        print(f"Error al revisar el catálogo de CDs: {e}")

    # Si hay cambios registrados, notificar a Discord mencionando a @everyone
    if cambios_detectados:
        mensaje_final = "@everyone 🚨 **¡Novedades en el stock de The Warning!** 🚨\n\n" + "\n\n".join(cambios_detectados)
        enviar_discord(mensaje_final)
    else:
        print("Sin cambios en el estado del stock.")

    # Guardar estado actual para la siguiente ejecución
    guardar_estado_actual(estado_actual)

if __name__ == "__main__":
    verificar_estado()
