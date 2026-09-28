import os
import json
import requests

# URLs de Discord y Credenciales de Telegram desde Secrets
WEBHOOKS = [
    os.environ.get("DISCORD_WEBHOOK"),
    os.environ.get("DISCORD_WEBHOOK_2")
]

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

ARCHIVO_ESTADO = "estado.json"
TIPO_DE_CAMBIO_FALLBACK = 1520.00

# Definición de Tiendas / Regiones a consultar
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
        "handle": "everything-s-falling-pink-halo-vinyl",
        "path": "/products/everything-s-falling-pink-halo-vinyl"
    },
    {
        "id": "qotms_vinyl",
        "nombre": "Queen of the Murder Scene (Vinilo)",
        "handle": "queen-of-the-murder-scene-vinyl",
        "path": "/products/queen-of-the-murder-scene-vinyl"
    },
    {
        "id": "xxicb_vinyl",
        "nombre": "XXI Century Blood (Vinilo)",
        "handle": "century-blood-vinyl",
        "path": "/products/century-blood-vinyl"
    },
    {
        "id": "bluray_auditorio_nacional",
        "nombre": "Live From Auditorio Nacional CDMX (Blu-Ray 4K UHD)",
        "handle": "the-warning-live-from-auditorio-nacional-cdmx-documentary-blu-ray-4k-uhd",
        "path": "/products/the-warning-live-from-auditorio-nacional-cdmx-documentary-blu-ray-4k-uhd"
    }
]

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

def verificar_disponibilidad_variante(base_url, handle, country_code):
    """
    Obtiene la variante del producto mediante el endpoint JSON nativo de Shopify
    e intenta simular la validación de inventario directo.
    """
    url_js = f"{base_url}/products/{handle}.js"
    url_web = f"{base_url}/products/{handle}"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "X-Requested-With": "XMLHttpRequest"
    }
    
    cookies = {
        "cart_currency": "USD",
        "localization": country_code
    }

    disponible = False
    precio_usd = 0.0

    # 1. Probar vía /products/{handle}.js (Endpoint ultra ligero de Shopify)
    try:
        res = requests.get(url_js, headers=headers, cookies=cookies, params={"country": country_code}, timeout=10)
        if res.status_code == 200:
            data = res.json()
            variants = data.get("variants", [])
            for v in variants:
                if v.get("available") is True:
                    disponible = True
                    precio_usd = float(v.get("price", 0)) / 100.0 if float(v.get("price", 0)) > 1000 else float(v.get("price", 0))
                    break
            
            if not disponible and variants:
                precio_usd = float(variants[0].get("price", 0)) / 100.0 if float(variants[0].get("price", 0)) > 1000 else float(variants[0].get("price", 0))

            if disponible:
                return disponible, precio_usd, url_web
    except Exception as e:
        print(f"Error consultando endpoint .js para {handle}: {e}")

    # 2. Probar vía /products/{handle}.json (Endpoint oficial)
    try:
        url_json = f"{base_url}/products/{handle}.json"
        res_json = requests.get(url_json, headers=headers, cookies=cookies, timeout=10)
        if res_json.status_code == 200:
            data = res_json.json().get("product", {})
            variants = data.get("variants", [])
            for v in variants:
                if v.get("available") is True:
                    disponible = True
                    precio_usd = float(v.get("price", 0))
                    break
            if not disponible and variants and precio_usd == 0.0:
                precio_usd = float(variants[0].get("price", 0))
    except Exception as e:
        print(f"Error consultando JSON para {handle}: {e}")

    return disponible, precio_usd, url_web

def formatear_precio(precio_usd, tipo_cambio):
    if precio_usd > 0:
        precio_ars = precio_usd * tipo_cambio
        return f"${precio_usd:.2f} USD (~${precio_ars:,.0f} ARS)"
    return "Precio N/A"

def verificar_estado():
    es_prueba_manual = os.environ.get("GITHUB_EVENT_NAME") == "workflow_dispatch"
    tipo_cambio_actual = obtener_tipo_de_cambio_ars()

    estado_anterior = cargar_estado_anterior()
    estado_actual = {}
    hay_cambios = False

    reportes_por_tienda = []

    # Iterar por cada región / tienda de forma independiente
    for tienda in TIENDAS:
        lineas_tienda = [f"### {tienda['nombre']}"]
        
        for prod in PRODUCTOS_SHOPIFY:
            clave_estado = f"{prod['id']}_{tienda['id']}"
            disp, precio_usd, url_web = verificar_disponibilidad_variante(
                tienda["base_url"], 
                prod["handle"], 
                tienda["country"]
            )
            
            estado_actual[clave_estado] = disp
            if estado_anterior.get(clave_estado) != disp:
                hay_cambios = True

            precio_fmt = formatear_precio(precio_usd, tipo_cambio_actual)
            
            if disp:
                lineas_tienda.append(f"  🟢 **[{prod['nombre']}]({url_web})**: ¡DISPONIBLE! — {precio_fmt}")
            else:
                lineas_tienda.append(f"  🔴 **[{prod['nombre']}]({url_web})**: Agotado — {precio_fmt}")

        reportes_por_tienda.append("\n".join(lineas_tienda))

    # Notificar si es ejecución manual o si cambió el estado en alguna región
    if es_prueba_manual or hay_cambios:
        encabezado = "🧪 **[PRUEBA MANUAL] Reporte de Stock por Regiones:**" if es_prueba_manual else "🚨 **¡Novedades de Stock detectadas!**"
        
        cuerpo_mensaje = "\n\n".join(reportes_por_tienda)
        mensaje_discord = f"@everyone {encabezado}\n\n{cuerpo_mensaje}"
        mensaje_telegram = f"{encabezado}\n\n{cuerpo_mensaje}"
        
        enviar_discord(mensaje_discord)
        enviar_telegram(mensaje_telegram)
    else:
        print("Sin cambios de estado en ninguna región. No se enviaron mensajes.")

    guardar_estado_actual(estado_actual)

if __name__ == "__main__":
    verificar_estado()
