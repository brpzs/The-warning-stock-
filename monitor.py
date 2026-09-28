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

ARCHIVO_ESTADO = "estado.json"
TIPO_DE_CAMBIO_FALLBACK = 1520.00

# Definición de Tiendas / Regiones a consultar
TIENDAS = [
    {
        "id": "us",
        "nombre": "🌐 Global / Estados Unidos",
        "base_url": "https://thewarningband.com",
        "params": {}
    },
    {
        "id": "mx",
        "nombre": "🇲🇽 México",
        "base_url": "https://thewarningband.com",
        "params": {"country": "MX"}
    },
    {
        "id": "uk",
        "nombre": "🇬🇧 Reino Unido / Europa",
        "base_url": "https://shopuk.thewarningband.com",
        "params": {}
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

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9,es;q=0.8"
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

def revisar_producto_en_tienda(tienda, handle, path):
    """Consulta la disponibilidad y precio de un producto analizando HTML, Schema JSON-LD y JSON de Shopify."""
    url_web = f"{tienda['base_url']}{path}"
    url_json = f"{tienda['base_url']}/products/{handle}.json"
    
    disponible = False
    precio_usd = 0.0

    cookies = {}
    if "country" in tienda.get("params", {}):
        cookies["localization"] = tienda["params"]["country"]

    # 1. Inspección prioritaria del HTML (Renderizado de Shopify)
    try:
        res_html = requests.get(url_web, headers=headers, params=tienda["params"], cookies=cookies, timeout=10)
        if res_html.status_code == 200:
            soup = BeautifulSoup(res_html.text, "html.parser")

            # A) Buscar en scripts de datos structured (JSON-LD)
            scripts_ld = soup.find_all("script", type="application/ld+json")
            for script in scripts_ld:
                if script.string:
                    try:
                        data = json.loads(script.string)
                        # Soporta si viene como lista o diccionario
                        items = data if isinstance(data, list) else [data]
                        for item in items:
                            offers = item.get("offers", [])
                            if isinstance(offers, dict):
                                offers = [offers]
                            for offer in offers:
                                avail = offer.get("availability", "")
                                if "InStock" in avail:
                                    disponible = True
                                if "price" in offer:
                                    try:
                                        precio_usd = float(offer["price"])
                                    except ValueError:
                                        pass
                    except Exception:
                        pass

            # B) Inspeccionar meta tag og:availability
            meta_avail = soup.find("meta", property="og:availability") or soup.find("meta", property="product:availability")
            if meta_avail and meta_avail.get("content"):
                if "instock" in meta_avail["content"].lower():
                    disponible = True

            # C) Extraer precio desde meta-tags si no se obtuvo antes
            if precio_usd == 0.0:
                meta_precio = soup.find("meta", property="og:price:amount") or soup.find("meta", property="product:price:amount")
                if meta_precio and meta_precio.get("content"):
                    try:
                        precio_usd = float(meta_precio["content"])
                    except ValueError:
                        pass

            # D) Inspección de botón 'Añadir al carrito'
            if not disponible:
                btn_comprar = (
                    soup.find("button", {"name": "add"}) or 
                    soup.find("button", id=lambda x: x and "add-to-cart" in str(x).lower()) or
                    soup.find("button", class_=lambda x: x and "add-to-cart" in str(x).lower())
                )
                if btn_comprar:
                    texto_btn = btn_comprar.get_text(strip=True).lower()
                    es_disabled = btn_comprar.has_attr("disabled") or btn_comprar.get("aria-disabled") == "true"
                    if not es_disabled and "sold out" not in texto_btn and "agotado" not in texto_btn:
                        disponible = True

            if disponible:
                return disponible, precio_usd, url_web
    except Exception as e:
        print(f"Error consultando HTML para {handle} en {tienda['nombre']}: {e}")

    # 2. Respaldo por la API JSON de Shopify si el HTML no arrojó stock
    try:
        res = requests.get(url_json, headers=headers, params=tienda["params"], cookies=cookies, timeout=10)
        if res.status_code == 200:
            datos = res.json().get("product", {})
            variantes = datos.get("variants", [])
            for v in variantes:
                if v.get("available") is True:
                    disponible = True
                    precio_usd = float(v.get("price", 0))
                    break
            if not disponible and variantes and precio_usd == 0.0:
                precio_usd = float(variantes[0].get("price", 0))
    except Exception as e:
        print(f"Error consultando JSON para {handle} en {tienda['nombre']}: {e}")

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
            disp, precio_usd, url_web = revisar_producto_en_tienda(tienda, prod["handle"], prod["path"])
            
            estado_actual[clave_estado] = disp
            if estado_anterior.get(clave_estado) != disp:
                hay_cambios = True

            precio_fmt = formatear_precio(precio_usd, tipo_cambio_actual)
            
            if disp:
                lineas_tienda.append(f"  🟢 **[{prod['nombre']}]({url_web})**: ¡DISPONIBLE! — {precio_fmt}")
            else:
                lineas_tienda.append(f"  🔴 **[{prod['nombre']}]({url_web})**: Agotado — {precio_fmt}")

        reportes_por_tienda.append("\n".join(lineas_tienda))

    # Revisar la sección de CDs (solo en tienda Principal)
    try:
        url_musica = "https://thewarningband.com/collections/music"
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
                    url_cd_qotms = href if href.startswith("http") else f"https://thewarningband.com{href}"
                if ("century" in href_lower or "xxicb" in href_lower) and "cd" in href_lower:
                    url_cd_xxicb = href if href.startswith("http") else f"https://thewarningband.com{href}"

        lineas_cds = ["### 💿 Sección CDs (Tienda Oficial)"]
        
        # CD QOTMS
        qotms_cd_disponible = url_cd_qotms is not None
        estado_actual["qotms_cd"] = qotms_cd_disponible
        if estado_anterior.get("qotms_cd") != qotms_cd_disponible:
            hay_cambios = True
        
        if qotms_cd_disponible:
            lineas_cds.append(f"  🟢 **[Queen of the Murder Scene (CD)]({url_cd_qotms})**: ¡DISPONIBLE!")
        else:
            lineas_cds.append(f"  🔴 **[Queen of the Murder Scene (CD)]({url_musica})**: No disponible")

        # CD XXI Century Blood
        xxicb_cd_disponible = url_cd_xxicb is not None
        estado_actual["xxicb_cd"] = xxicb_cd_disponible
        if estado_anterior.get("xxicb_cd") != xxicb_cd_disponible:
            hay_cambios = True
            
        if xxicb_cd_disponible:
            lineas_cds.append(f"  🟢 **[XXI Century Blood (CD)]({url_cd_xxicb})**: ¡DISPONIBLE!")
        else:
            lineas_cds.append(f"  🔴 **[XXI Century Blood (CD)]({url_musica})**: No disponible")

        reportes_por_tienda.append("\n".join(lineas_cds))

    except Exception as e:
        print(f"Error al revisar catálogo de CDs: {e}")

    # Notificar si es ejecución manual o si cambió el stock en alguna región
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
