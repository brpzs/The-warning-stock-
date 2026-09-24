import os
import json
import requests
from bs4 import BeautifulSoup

# URLs de Discord y Credenciales de Telegram desde Secrets
WEBHOOKS = [
    os.environ.get("DISCORD_WEBHOOK"),
    os.environ.get("DISCORD_WEBHOOK_2")
]

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

BASE_URL = "https://thewarningband.com"
ARCHIVO_ESTADO = "estado.json"

# Valor por defecto si la API de dólares no responde
TIPO_DE_CAMBIO_FALLBACK = 1520.00

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

def obtener_tipo_de_cambio_ars():
    """Consulta la cotización actual del Dólar Tarjeta desde DolarApi"""
    try:
        res = requests.get("https://dolarapi.com/v1/dolares/tarjeta", timeout=5)
        if res.status_code == 200:
            datos = res.json()
            cotizacion = float(datos.get("venta", 0))
            if cotizacion > 0:
                print(f"💱 Cotización Dólar Tarjeta: ${cotizacion:,.2f} ARS")
                return cotizacion
    except Exception as e:
        print(f"⚠️ Error obteniendo cotización del dólar ({e}). Usando valor por defecto.")
    return TIPO_DE_CAMBIO_FALLBACK

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
    payload = {"content": mensaje}
    for url in WEBHOOKS:
        if url:
            try:
                res = requests.post(url, json=payload)
                if res.status_code in [200, 204]:
                    print("✅ Mensaje enviado exitosamente a servidor de Discord.")
                else:
                    print(f"⚠️ Error al enviar a Discord ({res.status_code}): {res.text}")
            except Exception as e:
                print(f"❌ Excepción enviando a Discord: {e}")

def enviar_telegram(mensaje):
    if TELEGRAM_TOKEN and TELEGRAM_CHAT_ID:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": mensaje,
            "parse_mode": "Markdown",
            "disable_web_page_preview": True
        }
        try:
            res = requests.post(url, json=payload, timeout=10)
            if res.status_code == 200:
                print("✅ Mensaje enviado exitosamente a Telegram.")
            else:
                print(f"⚠️ Error enviando a Telegram ({res.status_code}): {res.text}")
        except Exception as e:
            print(f"❌ Excepción enviando a Telegram: {e}")

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

def formatear_precio(precio_usd, tipo_cambio):
    if precio_usd > 0:
        precio_ars = precio_usd * tipo_cambio
        return f"💵 **${precio_usd:.2f} USD** *(~${precio_ars:,.0f} ARS)*"
    return "Precio N/A"

def verificar_estado():
    es_prueba_manual = os.environ.get("GITHUB_EVENT_NAME") == "workflow_dispatch"
    tipo_cambio_actual = obtener_tipo_de_cambio_ars()

    estado_anterior = cargar_estado_anterior()
    estado_actual = {}
    hay_cambios = False

    reporte_lineas = []

    # 1. Revisar Vinilos
    for prod in VINILOS:
        disponible, precio_usd = obtener_datos_producto_shopify(prod["handle"])
        estado_actual[prod["id"]] = disponible
        info_precio = formatear_precio(precio_usd, tipo_cambio_actual)
        
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

    # Notificar si es prueba manual o si hubo cambio de estado
    if es_prueba_manual or hay_cambios:
        encabezado = "🧪 **[PRUEBA MANUAL] Reporte Actual de Stock:**" if es_prueba_manual else "🚨 **¡Novedades de Stock detectadas!**"
        
        mensaje_discord = f"@everyone {encabezado}\n\n" + "\n\n".join(reporte_lineas)
        mensaje_telegram = f"{encabezado}\n\n" + "\n\n".join(reporte_lineas)
        
        enviar_discord(mensaje_discord)
        enviar_telegram(mensaje_telegram)
    else:
        print("Sin cambios de estado en la revisión automática. No se enviaron mensajes.")

    guardar_estado_actual(estado_actual)

if __name__ == "__main__":
    verificar_estado()
