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
from urllib.parse import urljoin, urlparse

class RobustAmazonMonitor:
    def __init__(self):
        # Rotar entre múltiples User Agents
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        ]
        
        self.email_user = os.environ.get('EMAIL_USER')
        self.email_pass = os.environ.get('EMAIL_PASS')
        self.recipient_email = os.environ.get('RECIPIENT_EMAIL')
        
    def get_headers(self):
        """Genera headers aleatorios para cada request"""
        return {
            'User-Agent': random.choice(self.user_agents),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': random.choice(['es-ES,es;q=0.9,en;q=0.8', 'en-US,en;q=0.9', 'es-AR,es;q=0.9']),
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Cache-Control': 'max-age=0',
        }
    
    def clean_amazon_url(self, url):
        """Limpia la URL de Amazon para que sea más simple"""
        if '/dp/' in url:
            # Extraer solo el ASIN
            asin = url.split('/dp/')[1].split('/')[0].split('?')[0]
            domain = urlparse(url).netloc
            return f"https://{domain}/dp/{asin}"
        elif '/gp/product/' in url:
            asin = url.split('/gp/product/')[1].split('/')[0].split('?')[0]
            domain = urlparse(url).netloc
            return f"https://{domain}/dp/{asin}"
        return url
    
    def load_products(self):
        try:
            with open('config.json', 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            print("❌ Archivo config.json no encontrado")
            return {"products": []}
    
    def extract_price_from_text(self, text):
        """Extrae precio de cualquier texto usando regex"""
        # Patrones para diferentes formatos de precio
        patterns = [
            r'(\d+[.,]\d{2})\s*€',  # 123,45 €
            r'€\s*(\d+[.,]\d{2})',  # € 123,45
            r'(\d+[.,]\d{2})',      # Solo número
            r'(\d+)\s*€',           # 123 €
            r'€\s*(\d+)',           # € 123
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text)
            if matches:
                price_str = matches[0].replace(',', '.')
                try:
                    return float(price_str)
                except ValueError:
                    continue
        return None
    
    def get_price_multiple_methods(self, url):
        """Múltiples métodos para obtener precio"""
        url = self.clean_amazon_url(url)
        print(f"   🔍 URL limpia: {url}")
        
        methods = [
            self.method_1_standard_selectors,
            self.method_2_text_search,
            self.method_3_json_extraction,
            self.method_4_all_text_scan
        ]
        
        for i, method in enumerate(methods, 1):
            try:
                print(f"   🔄 Probando método {i}...")
                price = method(url)
                if price:
                    print(f"   ✅ Método {i} exitoso: €{price}")
                    return price
                else:
                    print(f"   ❌ Método {i} sin resultado")
            except Exception as e:
                print(f"   ⚠️ Método {i} error: {e}")
            
            # Pausa entre métodos
            time.sleep(random.uniform(1, 3))
        
        return None
    
    def method_1_standard_selectors(self, url):
        """Método 1: Selectores CSS estándar"""
        headers = self.get_headers()
        response = requests.get(url, headers=headers, timeout=15)
        
        if response.status_code != 200:
            return None
            
        soup = BeautifulSoup(response.content, 'html.parser')
        
        selectors = [
            '.a-price-whole',
            '.a-price .a-offscreen',
            '.a-price-range .a-price .a-offscreen',
            '#priceblock_dealprice',
            '#priceblock_ourprice',
            '[data-a-price] .a-offscreen',
            '.a-price.a-text-price .a-offscreen',
            '.a-price-symbol',
            '.a-price .a-price-whole',
            'span[aria-label*="precio"]',
            'span[aria-label*="price"]'
        ]
        
        for selector in selectors:
            elements = soup.select(selector)
            for element in elements:
                price = self.extract_price_from_text(element.get_text())
                if price and price > 1:  # Precio razonable
                    return price
        
        return None
    
    def method_2_text_search(self, url):
        """Método 2: Búsqueda en todo el texto"""
        headers = self.get_headers()
        response = requests.get(url, headers=headers, timeout=15)
        
        if response.status_code != 200:
            return None
            
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Buscar en elementos que contengan "precio" o símbolos de euro
        euro_elements = soup.find_all(text=re.compile(r'[€$]\s*\d+|Price|precio|EUR', re.I))
        
        for element in euro_elements:
            price = self.extract_price_from_text(str(element))
            if price and price > 1:
                return price
        
        return None
    
    def method_3_json_extraction(self, url):
        """Método 3: Extraer de JSON embebido"""
        headers = self.get_headers()
        response = requests.get(url, headers=headers, timeout=15)
        
        if response.status_code != 200:
            return None
        
        # Buscar JSON con datos estructurados
        json_patterns = [
            r'"price":\s*"([^"]*)"',
            r'"price":\s*([0-9.]+)',
            r'"priceAmount":\s*([0-9.]+)',
            r'"value":\s*([0-9.]+)',
        ]
        
        for pattern in json_patterns:
            matches = re.findall(pattern, response.text)
            for match in matches:
                price = self.extract_price_from_text(str(match))
                if price and price > 1:
                    return price
        
        return None
    
    def method_4_all_text_scan(self, url):
        """Método 4: Escaneo completo de texto"""
        headers = self.get_headers()
        response = requests.get(url, headers=headers, timeout=15)
        
        if response.status_code != 200:
            return None
            
        # Buscar todos los precios en el HTML completo
        price_matches = re.findall(r'(\d+[.,]\d{2})\s*€', response.text)
        
        if price_matches:
            prices = []
            for match in price_matches:
                try:
                    price = float(match.replace(',', '.'))
                    if 5 <= price <= 10000:  # Rango razonable
                        prices.append(price)
                except ValueError:
                    continue
            
            if prices:
                # Retornar el precio más común o el primero válido
                return min(prices)  # O max(prices) o prices[0]
        
        return None
    
    def send_notification(self, alerts):
        if not alerts or not all([self.email_user, self.email_pass, self.recipient_email]):
            print("⚠️ Sin alertas o configuración de email incompleta")
            return
        
        try:
            msg = MIMEMultipart()
            msg['From'] = self.email_user
            msg['To'] = self.recipient_email
            msg['Subject'] = f"🎉 ¡{len(alerts)} producto(s) con precio reducido!"
            
            body = "¡Hola! Los siguientes productos han alcanzado tu precio objetivo:\n\n"
            
            for alert in alerts:
                body += f"🛍️ {alert['title']}\n"
                body += f"   💰 Precio actual: €{alert['current_price']}\n"
                body += f"   🎯 Precio objetivo: €{alert['target_price']}\n"
                body += f"   💸 Ahorras: €{alert['target_price'] - alert['current_price']:.2f}\n"
                body += f"   🔗 {alert['url']}\n\n"
            
            body += f"Revisado el: {datetime.now().strftime('%d/%m/%Y %H:%M')}"
            
            msg.attach(MIMEText(body, 'plain', 'utf-8'))
            
            server = smtplib.SMTP('smtp.gmail.com', 587)
            server.starttls()
            server.login(self.email_user, self.email_pass)
            server.send_message(msg)
            server.quit()
            
            print("✅ Email enviado correctamente")
            
        except Exception as e:
            print(f"❌ Error al enviar email: {e}")
    
    def save_dashboard_data(self, products, alerts):
        print("💾 Guardando datos para dashboard...")
        
        os.makedirs('docs/data', exist_ok=True)
        
        current_data = {
            "last_update": datetime.now().isoformat(),
            "products": [],
            "alerts_count": len(alerts),
            "total_products": len(products)
        }
        
        total_savings = 0
        
        for product in products:
            current_price = self.get_price_multiple_methods(product['url'])
            is_alert = current_price and current_price <= product['target_price']
            
            if is_alert:
                total_savings += (product['target_price'] - current_price)
            
            current_data["products"].append({
                "name": product.get('name', 'Sin nombre'),
                "url": product['url'],
                "current_price": current_price,
                "target_price": product['target_price'],
                "alert": is_alert,
                "last_checked": datetime.now().isoformat()
            })
        
        current_data["total_savings"] = round(total_savings, 2)
        
        # Guardar datos actuales
        with open('docs/data/current-prices.json', 'w', encoding='utf-8') as f:
            json.dump(current_data, f, ensure_ascii=False, indent=2)
        
        # Historial
        history_file = 'docs/data/price-history.json'
        try:
            with open(history_file, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                if content:
                    history_data = json.loads(content)
                else:
                    history_data = {"history": {}}
        except (FileNotFoundError, json.JSONDecodeError):
            history_data = {"history": {}}
        
        today = datetime.now().strftime('%Y-%m-%d')
        for product_data in current_data["products"]:
            if product_data["current_price"]:
                product_name = product_data["name"]
                if product_name not in history_data["history"]:
                    history_data["history"][product_name] = []
                
                today_entry = {
                    "date": today,
                    "datetime": datetime.now().isoformat(),
                    "price": product_data["current_price"]
                }
                
                existing_today = next((entry for entry in history_data["history"][product_name] 
                                     if entry["date"] == today), None)
                
                if existing_today:
                    existing_today["price"] = product_data["current_price"]
                    existing_today["datetime"] = datetime.now().isoformat()
                else:
                    history_data["history"][product_name].append(today_entry)
                
                history_data["history"][product_name] = history_data["history"][product_name][-30:]
        
        with open(history_file, 'w', encoding='utf-8') as f:
            json.dump(history_data, f, ensure_ascii=False, indent=2)
        
        print("✅ Dashboard actualizado")
    
    def run(self):
        print("🔍 Iniciando monitoreo robusto...")
        print(f"📅 {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
        print("-" * 60)
        
        config = self.load_products()
        products = config.get('products', [])
        
        if not products:
            print("❌ No hay productos en config.json")
            return
        
        alerts = []
        
        for i, product in enumerate(products, 1):
            print(f"\n[{i}/{len(products)}] 🛍️ {product.get('name', 'Sin nombre')}")
            
            # Pausa aleatoria entre productos
            if i > 1:
                delay = random.uniform(3, 8)
                print(f"   ⏳ Esperando {delay:.1f}s...")
                time.sleep(delay)
            
            current_price = self.get_price_multiple_methods(product['url'])
            target_price = product['target_price']
            
            if current_price:
                print(f"   💰 Precio actual: €{current_price}")
                print(f"   🎯 Precio objetivo: €{target_price}")
                
                if current_price <= target_price:
                    print(f"   🎉 ¡PRECIO OBJETIVO ALCANZADO!")
                    alerts.append({
                        'title': product.get('name', 'Producto'),
                        'current_price': current_price,
                        'target_price': target_price,
                        'url': product['url']
                    })
                else:
                    diff = current_price - target_price
                    print(f"   ⏳ Faltan €{diff:.2f} para alcanzar objetivo")
            else:
                print(f"   ❌ No se pudo obtener precio con ningún método")
        
        print(f"\n{'='*60}")
        
        # Guardar datos dashboard
        self.save_dashboard_data(products, alerts)
        
        # Enviar emails
        if alerts:
            print(f"📧 Enviando notificación para {len(alerts)} producto(s)")
            self.send_notification(alerts)
        else:
            print("😴 Ningún producto alcanzó el precio objetivo")
        
        print("✅ Monitoreo completado exitosamente")

if __name__ == "__main__":
    monitor = RobustAmazonMonitor()
    monitor.run()