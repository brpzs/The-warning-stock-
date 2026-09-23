import json
import os
import re
import urllib.request

WEBHOOK = os.environ["DISCORD_WEBHOOK"]

PRODUCTS = {
    "Queen of the Murder Scene Vinyl":
        "https://thewarningband.com/products/queen-of-the-murder-scene-vinyl",
    "Century Blood Vinyl":
        "https://thewarningband.com/products/century-blood-vinyl",
}

STATE_FILE = "state.json"


def get_page(url):
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0"}
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        return response.read().decode("utf-8", errors="ignore")


def get_product(url):
    request = urllib.request.Request(
        url + ".js",
        headers={"User-Agent": "Mozilla/5.0"}
    )

    with urllib.request.urlopen(request, timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))


def send_discord(message):
    data = json.dumps({
        "content": message
    }).encode("utf-8")

    request = urllib.request.Request(
        WEBHOOK,
        data=data,
        headers={
            "Content-Type": "application/json",
            "User-Agent": "TheWarningStockBot/1.0"
        },
        method="POST"
    )

    urllib.request.urlopen(request, timeout=20).read()


def load_state():
    if not os.path.exists(STATE_FILE):
        return {}

    with open(STATE_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)


def usd_to_ars(usd):
    try:
        request = urllib.request.Request(
            "https://api.frankfurter.app/latest?from=USD&to=ARS",
            headers={"User-Agent": "TheWarningStockBot/1.0"}
        )

        with urllib.request.urlopen(request, timeout=20) as response:
            data = json.loads(response.read().decode())

        return usd * data["rates"]["ARS"]

    except Exception:
        return None


def main():
    state = load_state()

    for name, url in PRODUCTS.items():

        try:
            product = get_product(url)

            available = any(
                variant.get("available", False)
                for variant in product.get("variants", [])
            )

            price = float(product["price"]) / 100

            previous = state.get(name)

            # Primera ejecución: guardar estado sin mandar alerta.
            if previous is None:
                state[name] = available
                continue

            # Detectar agotado -> disponible
            if previous is False and available is True:

                ars = usd_to_ars(price)

                ars_text = (
                    f"${ars:,.0f} ARS".replace(",", ".")
                    if ars
                    else "No disponible"
                )

                message = (
                    "🚨 **¡VOLVIÓ EL STOCK!**\n\n"
                    f"💿 **{name}**\n"
                    f"💵 US${price:.2f}\n"
                    f"🇦🇷 ≈ {ars_text}\n"
                    f"🔗 {url}"
                )

                send_discord(message)

            state[name] = available

        except Exception as error:
            print(f"Error comprobando {name}: {error}")

    save_state(state)


if __name__ == "__main__":
    main()
