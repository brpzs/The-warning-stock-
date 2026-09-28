def enviar_discord(mensaje):
    payload = {
        "content": mensaje,
        "allowed_mentions": {"parse": []}  # Evita bloqueos de menciones
    }
    for url in WEBHOOKS:
        if url and url.strip():
            try:
                res = requests.post(url.strip(), json=payload, timeout=10)
                print(f"Status Discord: {res.status_code}")
                if res.status_code not in [200, 204]:
                    print(f"⚠️ Detalle error Discord: {res.text}")
            except Exception as e:
                print(f"❌ Excepción enviando a Discord: {e}")

def enviar_telegram(mensaje):
    if TELEGRAM_TOKEN and TELEGRAM_CHAT_ID:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN.strip()}/sendMessage"
        # Enviamos sin parse_mode para evitar que caracteres especiales tumben el mensaje
        payload = {
            "chat_id": TELEGRAM_CHAT_ID.strip(),
            "text": mensaje,
            "disable_web_page_preview": True
        }
        try:
            res = requests.post(url, json=payload, timeout=10)
            print(f"Status Telegram: {res.status_code}")
            if res.status_code != 200:
                print(f"⚠️ Detalle error Telegram: {res.text}")
        except Exception as e:
            print(f"❌ Excepción enviando a Telegram: {e}")

def verificar_estado():
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

    print(f"DEBUG: Es prueba manual? {es_prueba_manual} | Hubo cambios? {hay_cambios}")

    if es_prueba_manual or hay_cambios:
        encabezado = "🧪 [PRUEBA MANUAL] Reporte de Stock por Regiones:" if es_prueba_manual else "🚨 ¡Novedades de Stock detectadas!"
        cuerpo_mensaje = "\n\n".join(reportes_por_tienda)
        
        mensaje_final = f"{encabezado}\n\n{cuerpo_mensaje}"
        
        print("Enviando notificaciones...")
        enviar_discord(mensaje_final)
        enviar_telegram(mensaje_final)
    else:
        print("Sin cambios de estado en ninguna región. No se enviaron mensajes.")

    guardar_estado_actual(estado_actual)
