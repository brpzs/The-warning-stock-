import os
import json
import sys

# Intentar importar requests
try:
    import requests
except ImportError:
    print("❌ ERROR: La librería 'requests' no está instalada.")
    sys.exit(1)

# Variables de entorno
WEBHOOKS = [
    os.environ.get("DISCORD_WEBHOOK"),
    os.environ.get("DISCORD_WEBHOOK_2")
]

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

ARCHIVO_ESTADO = "estado.json"
TIPO_DE_CAMBIO_FALLBACK = 1520.00

TIENDAS = [
    {
        "id": "us",
        "nombre": "🌐 Global / Estados Unidos",
        "base_url": "https://thewarningband.com",
        "country": "US"
    },
    {
        "id": "mx",
        "nombre": "🇲🇽 México",
        "base_url": "https://thewarningband.com",
        "country": "MX"
    },
    {
        "id": "uk",
        "nombre": "🇬🇧 Reino Unido / Europa",
        "base_url": "https://shopuk.thewarningband.com",
        "country": "GB"
    }
]

PRODUCTOS_SHOPIFY = [
    {
        "id": "ef_pink_halo_vinyl",
        "nombre": "Everything's Falling Pink Halo (Vinilo)",
        "handle": "everything-s-falling-pink-halo-vinyl"
    },
    {
        "id": "qotms_vinyl",
        "nombre": "Queen of the Murder Scene (Vinilo)",
        "handle": "queen-of-the-murder-scene-vinyl"
    },
    {
        "id": "xxicb_vinyl",
        "nombre": "XXI Century Blood (Vinilo)",
        "handle": "century-blood-vinyl"
    },
    {
        "id": "bluray_auditorio_nacional",
        "nombre": "Live From Auditorio Nacional CDMX (Blu-Ray 4K UHD)",
        "handle": "the-warning-live-from-auditorio-nacional-cdmx-documentary-blu-ray-4k-uhd"
    }
]

def obtener_tipo_de_cambio_ars():
    try:
        res = requests.get("https://dolarapi.com/v1/dolares/tarjeta", timeout=5)
        if res.status_code == 200:
            datos = res.json()
            cotizacion = float(datos.get("venta", 0))
            if cotizacion > 0:
                print(f"💱 Cotización Dólar Tarjeta: ${cotizacion:,.2f} ARS")
                return cotizacion
    except Exception as e:
        print(f"⚠️ Error obteniendo dólar ({e}). Usando fallback.")
    return TIPO_DE_CAMBIO_FALLBACK

def cargar_estado_anterior():
    if os.path.exists(ARCHIVO_ESTADO):
        try:
            with open(ARCHIVO_ESTADO, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"⚠️ Error leyendo estado anterior: {e}")
    return {}

def guardar_estado_actual(estado):
    try:
        with open(ARCHIVO_ESTADO, "w", encoding="utf-8") as f:
            json.dump(estado, f, indent=4, ensure_ascii=False)
        print("💾 Estado guardado en estado.json")
    except Exception as e:
        print(f"❌ Error guardando estado.json: {e}")

def enviar_discord(mensaje):
    payload = {
        "content": mensaje,
        "allowed_mentions": {"parse": []}
    }
    for url in WEBHOOKS:
        if url and url.strip():
            try:
                res = requests.post(url.strip(), json=payload, timeout=10)
                print(f"📡 Discord HTTP Status: {res.status_code}")
                if res.status_code not in [200, 204]:
                    print(f"⚠️ Respuesta Discord: {res.text}")
            except Exception as e:
                print(f"❌ Excepción enviando a Discord: {e}")

def enviar_telegram(mensaje):
    if TELEGRAM_TOKEN and TELEGRAM_CHAT_ID:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN.strip()}/sendMessage"
        payload = {
            "chat_id": TELEGRAM_CHAT_ID.strip(),
            "text": mensaje,
            "disable_web_page_preview": True
        }
        try:
            res = requests.post(url, json=payload, timeout=10)
            print(f"📡 Telegram HTTP Status: {res.status_code}")
            if res.status_code != 200:
                print(f"⚠️ Respuesta Telegram: {res.text}")
        except Exception as e:
            print(f"❌ Excepción enviando a Telegram: {e}")
    else:
        print("⚠️ Faltan TELEGRAM_TOKEN o TELEGRAM_CHAT_ID.")

def verificar_disponibilidad_variante(base_url, handle, country_code):
    url_js = f"{base_url}/products/{handle}.js"
    url_web = f"{base_url}/products/{handle}"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0.0.0",
        "Accept": "application/json"
    }
    cookies = {
        "cart_currency": "USD",
        "localization": country_code
    }

    disponible = False
    precio_usd = 0.0

    try:
        res = requests.get(url_js, headers=headers, cookies=cookies, params={"country": country_code}, timeout=10)
        if res.status_code == 200:
            data = res.json()
            variants = data.get("variants", [])
            for v in variants:
                if v.get("available") is True:
                    disponible = True
                    precio_raw = float(v.get("price", 0))
                    precio_usd = precio_raw / 100.0 if precio_raw > 1000 else precio_raw
                    break
            if not disponible and variants:
                precio_raw = float(variants[0].get("price", 0))
                precio_usd = precio_raw / 100.0 if precio_raw > 1000 else precio_raw
    except Exception as e:
        print(f"⚠️ Error consultando {handle}: {e}")

    return disponible, precio_usd, url_web

def formatear_precio(precio_usd, tipo_cambio):
    if precio_usd > 0:
        precio_ars = precio_usd * tipo_cambio
        return f"${precio_usd:.2f} USD (~${precio_ars:,.0f} ARS)"
    return "Precio N/A"

def verificar_estado():
    print("--- INICIANDO VERIFICACIÓN DE STOCK ---")
    evento_github = os.environ.get("GITHUB_EVENT_NAME", "")
    es_prueba_manual = (evento_github == "workflow_dispatch")

    tipo_cambio_actual = obtener_tipo_de_cambio_ars()
    estado_anterior = cargar_estado_anterior()
    estado_actual = {}
    hay_cambios = False

    reportes_por_tienda = []

    for tienda in TIENDAS:
        lineas_tienda = [f"--- {tienda['nombre']} ---"]
        
        for prod in PRODUCTOS_SHOPIFY:
            clave_estado = f"{prod['id']}_{tienda['id']}"
            disp, precio_usd, url_web = verificar_disponibilidad_variante(
                tienda["base_url"], 
                prod["handle"], 
                tienda["country"]
            )
            
            estado_actual[clave_estado] = disp
            
            if clave_estado in estado_anterior:
                if estado_anterior[clave_estado] != disp:
                    hay_cambios = True
            else:
                hay_cambios = True

            precio_fmt = formatear_precio(precio_usd, tipo_cambio_actual)
            
            if disp:
                lineas_tienda.append(f"🟢 {prod['nombre']}: ¡DISPONIBLE! ({precio_fmt})\n🔗 {url_web}")
            else:
                lineas_tienda.append(f"🔴 {prod['nombre']}: Agotado ({precio_fmt})")

        reportes_por_tienda.append("\n".join(lineas_tienda))

    print(f"📊 Evaluando envío -> Prueba manual: {es_prueba_manual} | Hay cambios: {hay_cambios}")

    if es_prueba_manual or hay_cambios:
        encabezado = "🧪 [PRUEBA MANUAL] Reporte de Stock por Regiones:" if es_prueba_manual else "🚨 ¡Novedades de Stock detectadas!"
        cuerpo_mensaje = "\n\n".join(reportes_por_tienda)
        mensaje_final = f"{encabezado}\n\n{cuerpo_mensaje}"
        
        print("🚀 Enviando mensajes a Discord y Telegram...")
        enviar_discord(mensaje_final)
        enviar_telegram(mensaje_final)
    else:
        print("ℹ️ Sin cambios de estado en ninguna región. No se envían mensajes.")

    guardar_estado_actual(estado_actual)

if __name__ == "__main__":
    verificar_estado()
