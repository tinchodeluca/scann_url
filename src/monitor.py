def save_dashboard_data(self, products, alerts):
    """Guarda datos para el dashboard web"""
    import os
    import json
    from datetime import datetime
    
    # Asegurar que existe la carpeta docs/data
    os.makedirs('docs/data', exist_ok=True)
    
    # Datos actuales
    current_data = {
        "last_update": datetime.now().isoformat(),
        "products": [],
        "alerts_count": len(alerts)
    }
    
    for product in products:
        current_price = self.get_price(product['url'])
        current_data["products"].append({
            "name": product.get('name', 'Sin nombre'),
            "url": product['url'],
            "current_price": current_price,
            "target_price": product['target_price'],
            "alert": current_price <= product['target_price'] if current_price else False
        })
    
    # Guardar datos actuales
    with open('docs/data/current-prices.json', 'w', encoding='utf-8') as f:
        json.dump(current_data, f, ensure_ascii=False, indent=2)
    
    # Cargar y actualizar historial
    history_file = 'docs/data/price-history.json'
    try:
        with open(history_file, 'r', encoding='utf-8') as f:
            history_data = json.load(f)
    except FileNotFoundError:
        history_data = {"history": {}}
    
    # Agregar precios actuales al historial
    today = datetime.now().strftime('%Y-%m-%d')
    for product_data in current_data["products"]:
        if product_data["current_price"]:
            product_name = product_data["name"]
            if product_name not in history_data["history"]:
                history_data["history"][product_name] = []
            
            # Agregar entrada de hoy si no existe
            today_entry = {
                "date": today,
                "price": product_data["current_price"]
            }
            
            # Verificar si ya existe entrada para hoy
            existing_today = next((entry for entry in history_data["history"][product_name] if entry["date"] == today), None)
            
            if existing_today:
                existing_today["price"] = product_data["current_price"]
            else:
                history_data["history"][product_name].append(today_entry)
            
            # Mantener solo últimos 30 días
            history_data["history"][product_name] = history_data["history"][product_name][-30:]
    
    # Guardar historial actualizado
    with open(history_file, 'w', encoding='utf-8') as f:
        json.dump(history_data, f, ensure_ascii=False, indent=2)
    
    print("✅ Datos del dashboard actualizados")

# Agregar esta llamada al final del método monitor_all_products():
# self.save_dashboard_data(products, alerts)