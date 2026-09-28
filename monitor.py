import requests
from bs4 import BeautifulSoup

def consultar_producto(url):
    # Definimos cabeceras de navegador real
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
    }
    
    # Forzamos cookies de país/moneda para evitar geobloqueo de Shopify
    cookies = {
        "localization": "MX",  # o US / ES según la tienda principal
        "cart_currency": "USD"
    }

    try:
        response = requests.get(url, headers=headers, cookies=cookies, timeout=15)
        
        # Si Shopify devuelve 403 o error, lo registramos
        if response.status_code != 200:
            print(f"⚠️ Error {response.status_code} al acceder a {url}")
            return False

        html = response.text
        soup = BeautifulSoup(html, 'html.parser')

        # 1. Búsqueda por meta tag Schema.org (Google / Shopify standard)
        availability_meta = soup.find("meta", property="og:availability") or soup.find("meta", itemprop="availability")
        if availability_meta:
            content = availability_meta.get("content", "").lower()
            if "instock" in content:
                return True
            elif "outofstock" in content:
                return False

        # 2. Búsqueda en el botón de compra
        buy_button = soup.find("button", {"name": "add"}) or soup.find("button", id="AddToCart")
        if buy_button:
            if buy_button.has_attr("disabled") or "disabled" in buy_button.get("class", []):
                return False
            return True

        # Fallback por texto
        return "add to cart" in html.lower() or "añadir al carrito" in html.lower()

    except Exception as e:
        print(f"❌ Excepción al consultar {url}: {e}")
        return False
