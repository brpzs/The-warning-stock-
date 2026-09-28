def verificar_estado():
    # Lee explícitamente la variable que nos manda GitHub Actions
    evento_github = os.environ.get("GITHUB_EVENT_NAME", "")
    es_prueba_manual = (evento_github == "workflow_dispatch")

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
            
            # Comparamos si cambió respecto al estado guardado previamente
            if clave_estado in estado_anterior:
                if estado_anterior[clave_estado] != disp:
                    hay_cambios = True
            else:
                # Si es la primera vez que se registra el archivo, marca que hubo cambio inicial
                hay_cambios = True

            precio_fmt = formatear_precio(precio_usd, tipo_cambio_actual)
            
            if disp:
                lineas_tienda.append(f"  🟢 **[{prod['nombre']}]({url_web})**: ¡DISPONIBLE! — {precio_fmt}")
            else:
                lineas_tienda.append(f"  🔴 **[{prod['nombre']}]({url_web})**: Agotado — {precio_fmt}")

        reportes_por_tienda.append("\n".join(lineas_tienda))

    print(f"DEBUG: Es prueba manual? {es_prueba_manual} | Hubo cambios? {hay_cambios}")

    # MANDA MENSAJE SI ES PRUEBA MANUAL O SI DETECTÓ CAMBIOS
    if es_prueba_manual or hay_cambios:
        encabezado = "🧪 **[PRUEBA MANUAL] Reporte de Stock por Regiones:**" if es_prueba_manual else "🚨 **¡Novedades de Stock detectadas!**"
        
        cuerpo_mensaje = "\n\n".join(reportes_por_tienda)
        
        mensaje_discord = f"{encabezado}\n\n{cuerpo_mensaje}"
        mensaje_telegram = f"{encabezado}\n\n{cuerpo_mensaje}"
        
        enviar_discord(mensaje_discord)
        enviar_telegram(mensaje_telegram)
    else:
        print("Sin cambios de estado en ninguna región. No se enviaron mensajes.")

    guardar_estado_actual(estado_actual)
