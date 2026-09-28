def enviar_discord(mensaje):
    # Sanitizamos el mensaje para Discord
    payload = {
        "content": mensaje,
        "allowed_mentions": {"parse": ["everyone"]}
    }
    for url in WEBHOOKS:
        if url and url.strip():
            try:
                res = requests.post(url.strip(), json=payload, timeout=10)
                if res.status_code in [200, 204]:
                    print("✅ Mensaje enviado exitosamente a servidor de Discord.")
                else:
                    print(f"⚠️ Error al enviar a Discord ({res.status_code}): {res.text}")
            except Exception as e:
                print(f"❌ Excepción enviando a Discord: {e}")

def verificar_estado():
    es_prueba_manual = os.environ.get("GITHUB_EVENT_NAME") == "workflow_dispatch"
    tipo_cambio_actual = obtener_tipo_de_cambio_ars()

    estado_anterior = cargar_estado_anterior()
    estado_actual = {}
    hay_cambios = False

    reportes_por_tienda = []

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

    if es_prueba_manual or hay_cambios:
        encabezado = "🧪 **[PRUEBA MANUAL] Reporte de Stock por Regiones:**" if es_prueba_manual else "🚨 **¡Novedades de Stock detectadas!**"
        
        cuerpo_mensaje = "\n\n".join(reportes_por_tienda)
        
        # Mensaje formateado para Discord (sin forzar mención bloqueante)
        mensaje_discord = f"{encabezado}\n\n{cuerpo_mensaje}"
        
        # Mensaje para Telegram
        mensaje_telegram = f"{encabezado}\n\n{cuerpo_mensaje}"
        
        enviar_discord(mensaje_discord)
        enviar_telegram(mensaje_telegram)
    else:
        print("Sin cambios de estado en ninguna región. No se enviaron mensajes.")

    guardar_estado_actual(estado_actual)
