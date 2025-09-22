import requests
from bs4 import BeautifulSoup
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import json
import os
from datetime import datetime
import time
import random
import re
from urllib.parse import urlparse

class AmazonPriceExtractor:
    """Clase responsable únicamente de extraer precios de Amazon"""
    
    def __init__(self):
        self.session = requests.Session()
        self.setup_session()
    
    def setup_session(self):
        """Configura la sesión con headers realistas"""
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'es-ES,es;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        })
    
    def clean_url(self, url):
        """Limpia la URL de Amazon para usar solo el ASIN"""
        if '/dp/' in url:
            asin = url.split('/dp/')[1].split('/')[0].split('?')[0]
        elif '/gp/product/' in url:
            asin = url.split('/gp/product/')[1].split('/')[0].split('?')[0]
        else:
            return url
        
        domain = urlparse(url).netloc
        return f"https://{domain}/dp/{asin}"
    
    def get_page_content(self, url):
        """Obtiene el contenido HTML de la página"""
        clean_url = self.clean_url(url)
        
        try:
            # Pausa aleatoria para parecer humano
            time.sleep(random.uniform(1, 3))
            
            response = self.session.get(clean_url, timeout=15)
            
            if response.status_code == 200:
                return response.content
            else:
                print(f"   ⚠️ Status HTTP: {response.status_code}")
                return None
                
        except requests.RequestException as e:
            print(f"   ❌ Error de conexión: {e}")
            return None
    
    def extract_price(self, url):
        """Método principal para extraer precio"""
        content = self.get_page_content(url)
        if not content:
            return None
        
        soup = BeautifulSoup(content, 'html.parser')
        
        # Intentar diferentes métodos en orden de prioridad
        extractors = [
            self._extract_from_primary_selectors,
            self._extract_from_secondary_selectors,
            self._extract_from_json_data,
            self._extract_from_meta_tags
        ]
        
        for extractor in extractors:
            price = extractor(soup)
            if price and self._is_valid_price(price, soup):
                return price
        
        return None
    
    def _extract_from_primary_selectors(self, soup):
        """Extrae precio usando los selectores principales de Amazon"""
        primary_selectors = [
            '.a-price.a-text-price.a-size-medium.apexPriceToPay .a-offscreen',
            '.a-price.a-text-price .a-offscreen',
            'span.a-price-whole',
            '.a-price .a-offscreen'
        ]
        
        for selector in primary_selectors:
            element = soup.select_one(selector)
            if element:
                price = self._parse_price_text(element.get_text())
                if price:
                    print(f"   💰 Precio encontrado (selector primario): €{price}")
                    return price
        
        return None
    
    def _extract_from_secondary_selectors(self, soup):
        """Extrae precio usando selectores secundarios"""
        secondary_selectors = [
            '#price_inside_buybox',
            '#priceblock_dealprice',
            '#priceblock_ourprice',
            '[data-a-price] .a-offscreen'
        ]
        
        for selector in secondary_selectors:
            element = soup.select_one(selector)
            if element:
                price = self._parse_price_text(element.get_text())
                if price:
                    print(f"   💰 Precio encontrado (selector secundario): €{price}")
                    return price
        
        return None
    
    def _extract_from_json_data(self, soup):
        """Extrae precio de datos JSON embebidos"""
        scripts = soup.find_all('script', type='application/ld+json')
        
        for script in scripts:
            try:
                data = json.loads(script.string)
                price = self._find_price_in_json(data)
                if price:
                    print(f"   💰 Precio encontrado (JSON): €{price}")
                    return price
            except (json.JSONDecodeError, AttributeError):
                continue
        
        return None
    
    def _extract_from_meta_tags(self, soup):
        """Extrae precio de meta tags"""
        meta_selectors = [
            'meta[property="product:price:amount"]',
            'meta[name="price"]'
        ]
        
        for selector in meta_selectors:
            element = soup.select_one(selector)
            if element:
                price = self._parse_price_text(element.get('content', ''))
                if price:
                    print(f"   💰 Precio encontrado (meta): €{price}")
                    return price
        
        return None
    
    def _find_price_in_json(self, data):
        """Busca precio recursivamente en estructura JSON"""
        if isinstance(data, dict):
            for key, value in data.items():
                if key.lower() in ['price', 'priceamount']:
                    price = self._parse_price_text(str(value))
                    if price:
                        return price
                elif isinstance(value, (dict, list)):
                    price = self._find_price_in_json(value)
                    if price:
                        return price
        elif isinstance(data, list):
            for item in data:
                price = self._find_price_in_json(item)
                if price:
                    return price
        
        return None
    
    def _parse_price_text(self, text):
        """Convierte texto a precio numérico"""
        if not text:
            return None
        
        # Limpiar el texto
        cleaned = re.sub(r'[^\d,.]', '', str(text).strip())
        
        if not cleaned:
            return None
        
        try:
            # Manejar diferentes formatos de precio
            if ',' in cleaned and '.' in cleaned:
                # Determinar si es formato europeo (1.234,56) o americano (1,234.56)
                last_comma = cleaned.rfind(',')
                last_dot = cleaned.rfind('.')
                
                if last_comma > last_dot:
                    # Formato europeo: 1.234,56
                    cleaned = cleaned.replace('.', '').replace(',', '.')
                else:
                    # Formato americano: 1,234.56
                    cleaned = cleaned.replace(',', '')
            elif ',' in cleaned:
                # Solo coma: determinar si es decimal o separador de miles
                parts = cleaned.split(',')
                if len(parts) == 2 and len(parts[1]) == 2:
                    # Probablemente decimal: 123,45
                    cleaned = cleaned.replace(',', '.')
                else:
                    # Probablemente separador de miles: 1,234
                    cleaned = cleaned.replace(',', '')
            
            return float(cleaned)
            
        except ValueError:
            return None
    
    def _is_valid_price(self, price, soup):
        """Valida si el precio es razonable para el producto"""
        if not (5 <= price <= 5000):
            return False
        
        # Obtener título del producto para contexto
        title_element = soup.select_one('#productTitle')
        title = title_element.get_text().lower() if title_element else ""
        
        # Validaciones específicas según tipo de producto
        if any(word in title for word in ['4tb', '4 tb', 'disco', 'hdd', 'drive']):
            # Para discos duros 4TB, precio razonable entre 80-400 EUR
            return 80 <= price <= 400
        elif any(word in title for word in ['cable', 'adaptador', 'funda']):
            # Para accesorios, precio bajo puede ser normal
            return 5 <= price <= 100
        
        # Validación general: precio no puede ser demasiado bajo para electrónicos
        return price >= 10


class EmailNotifier:
    """Clase responsable de enviar notificaciones por email"""
    
    def __init__(self, email_user, email_pass, recipient_email):
        self.email_user = email_user
        self.email_pass = email_pass
        self.recipient_email = recipient_email
    
    def send_alert(self, alerts):
        """Envía alerta por email cuando hay productos con precio objetivo alcanzado"""
        if not alerts or not self._has_valid_credentials():
            return False
        
        try:
            msg = self._create_message(alerts)
            self._send_message(msg)
            print(f"✅ Email enviado: {len(alerts)} alerta(s)")
            return True
            
        except Exception as e:
            print(f"❌ Error enviando email: {e}")
            return False
    
    def _has_valid_credentials(self):
        """Verifica si las credenciales de email están configuradas"""
        return all([self.email_user, self.email_pass, self.recipient_email])
    
    def _create_message(self, alerts):
        """Crea el mensaje de email"""
        msg = MIMEMultipart()
        msg['From'] = self.email_user
        msg['To'] = self.recipient_email
        msg['Subject'] = f"🎉 {len(alerts)} producto(s) con precio objetivo alcanzado"
        
        body = self._create_body(alerts)
        msg.attach(MIMEText(body, 'plain', 'utf-8'))
        
        return msg
    
    def _create_body(self, alerts):
        """Crea el cuerpo del email"""
        body = "¡Hola! Los siguientes productos han alcanzado tu precio objetivo:\n\n"
        
        for alert in alerts:
            savings = alert['target_price'] - alert['current_price']
            body += f"🛍️ {alert['name']}\n"
            body += f"   💰 Precio actual: €{alert['current_price']:.2f}\n"
            body += f"   🎯 Precio objetivo: €{alert['target_price']:.2f}\n"
            body += f"   💸 Ahorras: €{savings:.2f}\n"
            body += f"   🔗 {alert['url']}\n\n"
        
        body += f"Revisado el: {datetime.now().strftime('%d/%m/%Y a las %H:%M')}\n"
        body += "Dashboard: https://tinchodeluca.github.io/scann_url/"
        
        return body
    
    def _send_message(self, msg):
        """Envía el mensaje por SMTP"""
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(self.email_user, self.email_pass)
        server.send_message(msg)
        server.quit()


class DashboardDataManager:
    """Clase responsable de manejar los datos del dashboard"""
    
    def __init__(self, data_dir='docs/data'):
        self.data_dir = data_dir
        self.current_prices_file = os.path.join(data_dir, 'current-prices.json')
        self.history_file = os.path.join(data_dir, 'price-history.json')
    
    def save_data(self, products_data, alerts):
        """Guarda los datos actuales y actualiza el historial"""
        os.makedirs(self.data_dir, exist_ok=True)
        
        current_data = self._prepare_current_data(products_data, alerts)
        self._save_current_data(current_data)
        self._update_history(current_data['products'])
        
        print("✅ Datos del dashboard actualizados")
    
    def _prepare_current_data(self, products_data, alerts):
        """Prepara los datos actuales"""
        total_savings = sum(
            (item['target_price'] - item['current_price']) 
            for item in products_data 
            if item['current_price'] and item['current_price'] <= item['target_price']
        )
        
        return {
            "last_update": datetime.now().isoformat(),
            "products": products_data,
            "alerts_count": len(alerts),
            "total_products": len(products_data),
            "total_savings": round(total_savings, 2)
        }
    
    def _save_current_data(self, data):
        """Guarda los datos actuales"""
        with open(self.current_prices_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def _update_history(self, products_data):
        """Actualiza el historial de precios"""
        try:
            with open(self.history_file, 'r', encoding='utf-8') as f:
                history_data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            history_data = {"history": {}}
        
        today = datetime.now().strftime('%Y-%m-%d')
        
        for product in products_data:
            if not product['current_price']:
                continue
            
            name = product['name']
            if name not in history_data["history"]:
                history_data["history"][name] = []
            
            # Actualizar o agregar entrada de hoy
            today_entry = {
                "date": today,
                "datetime": datetime.now().isoformat(),
                "price": product['current_price']
            }
            
            # Buscar si ya existe entrada para hoy
            existing = next(
                (entry for entry in history_data["history"][name] if entry["date"] == today), 
                None
            )
            
            if existing:
                existing.update(today_entry)
            else:
                history_data["history"][name].append(today_entry)
            
            # Mantener solo últimos 30 días
            history_data["history"][name] = history_data["history"][name][-30:]
        
        with open(self.history_file, 'w', encoding='utf-8') as f:
            json.dump(history_data, f, ensure_ascii=False, indent=2)


class AmazonPriceMonitor:
    """Clase principal que coordina todo el proceso de monitoreo"""
    
    def __init__(self):
        self.price_extractor = AmazonPriceExtractor()
        self.email_notifier = EmailNotifier(
            os.environ.get('EMAIL_USER'),
            os.environ.get('EMAIL_PASS'),
            os.environ.get('RECIPIENT_EMAIL')
        )
        self.dashboard_manager = DashboardDataManager()
    
    def run(self):
        """Ejecuta el proceso completo de monitoreo"""
        print("🔍 Iniciando monitor de precios Amazon")
        print(f"📅 {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
        print("=" * 60)
        
        # Cargar productos
        products = self._load_products()
        if not products:
            print("❌ No hay productos para monitorear")
            return
        
        # Procesar cada producto
        products_data = []
        alerts = []
        
        for i, product in enumerate(products, 1):
            print(f"\n[{i}/{len(products)}] 🛍️ {product.get('name', 'Sin nombre')}")
            
            result = self._process_product(product)
            products_data.append(result)
            
            if result['alert']:
                alerts.append(result)
        
        # Guardar datos y enviar notificaciones
        self._finish_monitoring(products_data, alerts)
    
    def _load_products(self):
        """Carga la configuración de productos"""
        try:
            with open('config.json', 'r', encoding='utf-8') as f:
                config = json.load(f)
                return config.get('products', [])
        except FileNotFoundError:
            print("❌ Archivo config.json no encontrado")
            return []
    
    def _process_product(self, product):
        """Procesa un producto individual"""
        name = product.get('name', 'Sin nombre')
        url = product['url']
        target_price = product['target_price']
        
        # Extraer precio
        current_price = self.price_extractor.extract_price(url)
        
        # Determinar si hay alerta
        is_alert = bool(current_price and current_price <= target_price)
        
        # Mostrar resultado
        if current_price:
            print(f"   💰 Precio actual: €{current_price:.2f}")
            print(f"   🎯 Precio objetivo: €{target_price:.2f}")
            
            if is_alert:
                savings = target_price - current_price
                print(f"   🎉 ¡OBJETIVO ALCANZADO! Ahorras €{savings:.2f}")
            else:
                diff = current_price - target_price
                print(f"   ⏳ Faltan €{diff:.2f} para el objetivo")
        else:
            print(f"   ❌ No se pudo obtener el precio")
        
        return {
            'name': name,
            'url': url,
            'current_price': current_price,
            'target_price': target_price,
            'alert': is_alert,
            'last_checked': datetime.now().isoformat()
        }
    
    def _finish_monitoring(self, products_data, alerts):
        """Finaliza el proceso de monitoreo"""
        print(f"\n{'='*60}")
        
        # Guardar datos del dashboard
        self.dashboard_manager.save_data(products_data, alerts)
        
        # Enviar notificaciones
        if alerts:
            print(f"📧 Enviando notificación para {len(alerts)} producto(s)")
            self.email_notifier.send_alert(alerts)
        else:
            print("😴 Ningún producto alcanzó el precio objetivo")
        
        print("✅ Monitoreo completado")


if __name__ == "__main__":
    monitor = AmazonPriceMonitor()
    monitor.run()