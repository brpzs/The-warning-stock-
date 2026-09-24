import os
import sys
import json
import requests
from bs4 import BeautifulSoup

DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK")

BASE_URL = "https://thewarningband.com"
ARCHIVO_ESTADO = "estado.json"

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
    # Detectar si fue lanzado manualmente desde GitHub Actions
    es_prueba_manual = os.environ.get("GITHUB_EVENT_NAME") == "workflow_dispatch"
    
    estado_anterior = cargar_estado_anterior()
    estado_actual = {}
    hay_cambios = False

    reporte_lineas = []

    # 1. Revisar Vinilos
    for prod in VINILOS:
        disponible, precio_usd = obtener_datos_producto_shopify(prod["handle"])
        estado_actual[prod["id"]] = disponible
        info_precio = formatear_precio(precio_usd)
        
        estaba_disponible = estado_anterior.get(prod["id"])
        if estaba_disponible != disponible:
            hay_cambios = True

        if disponible:
            reporte_lineas.append(f"🟢 **[{prod['nombre']}]({prod['url']})**: ¡DISPONIBLE! 🛒\n   └ Precio: {info_precio}")
        else:
            reporte_lineas.append(f"🔴 **[{prod['nombre']}]({prod['url']})**: Agotado\n   └ Precio: {info_precio}")

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
        if estado_anterior.get("qotms_cd") != qotms_cd_disponible:
            hay_cambios = True

        if qotms_cd_disponible:
            reporte_lineas.append(f"🟢 **[Queen of the Murder Scene (CD)]({url_cd_qotms})**: ¡DISPONIBLE!")
        else:
            reporte_lineas.append(f"🔴 **[Queen of the Murder Scene (CD)]({url_musica})**: No disponible")

        # CD XXI Century Blood
        xxicb_cd_disponible = url_cd_xxicb is not None
        estado_actual["xxicb_cd"] = xxicb_cd_disponible
        if estado_anterior.get("xxicb_cd") != xxicb_cd_disponible:
            hay_cambios = True

        if xxicb_cd_disponible:
            reporte_lineas.append(f"🟢 **[XXI Century Blood (CD)]({url_cd_xxicb})**: ¡DISPONIBLE!")
        else:
            reporte_lineas.append(f"🔴 **[XXI Century Blood (CD)]({url_musica})**: No disponible")

    except Exception as e:
        print(f"Error al revisar catálogo de CDs: {e}")

    # Decidir si se envía notificación a Discord
    if es_prueba_manual or hay_cambios:
        encabezado = "🧪 **[PRUEBA MANUAL] Reporte Actual de Stock:**" if es_prueba_manual else "🚨 **¡Novedades de Stock detectadas!**"
        
        mensaje_final = f"@everyone {encabezado}\n\n" + "\n\n".join(reporte_lineas)
        enviar_discord(mensaje_final)
        print("Notificación enviada a Discord exitosamente.")
    else:
        print("Sin cambios de estado en la revisión automática. No se envió mensaje.")

    guardar_estado_actual(estado_actual)

if __name__ == "__main__":
    verificar_estado()
