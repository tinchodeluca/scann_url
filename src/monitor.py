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

class GitHubAmazonMonitor:
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept-Language': 'es-ES,es;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        
        self.email_user = os.environ.get('EMAIL_USER')
        self.email_pass = os.environ.get('EMAIL_PASS')
        self.recipient_email = os.environ.get('RECIPIENT_EMAIL')
        
    def load_products(self):
        try:
            with open('config.json', 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            print("❌ Archivo config.json no encontrado")
            return {"products": []}
    
    def get_price(self, url):
        try:
            time.sleep(random.uniform(1, 3))
            
            response = requests.get(url, headers=self.headers, timeout=10)
            if response.status_code != 200:
                print(f"⚠️ Status code: {response.status_code}")
                return None
                
            soup = BeautifulSoup(response.content, 'html.parser')
            
            price_selectors = [
                'span.a-price.a-text-price.a-size-medium.apexPriceToPay .a-offscreen',
                'span.a-price-whole',
                '.a-price .a-offscreen',
                '#priceblock_dealprice',
                '#priceblock_ourprice',
                'span[class*="a-price-whole"]',
            ]
            
            for selector in price_selectors:
                elements = soup.select(selector)
                for element in elements:
                    price_text = element.get_text().strip()
                    if price_text:
                        clean_price = ''.join(c for c in price_text if c.isdigit() or c in '.,')
                        if clean_price:
                            if ',' in clean_price and '.' in clean_price:
                                clean_price = clean_price.replace('.', '').replace(',', '.')
                            elif ',' in clean_price:
                                clean_price = clean_price.replace(',', '.')
                            
                            try:
                                return float(clean_price)
                            except ValueError:
                                continue
            
            print(f"❌ No se pudo extraer el precio")
            return None
            
        except Exception as e:
            print(f"❌ Error al obtener precio: {e}")
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
                body += f"   🔗 {alert['url']}\n\n"
            
            body += f"Dashboard: https://{os.environ.get('GITHUB_REPOSITORY', '').replace('/', '.github.io/')}/\n"
            body += f"Revisado el: {datetime.now().strftime('%d/%m/%Y %H:%M')}"
            
            msg.attach(MIMEText(body, 'plain', 'utf-8'))
            
            server = smtplib.SMTP('smtp.gmail.com', 587)
            server.starttls()
            server.login(self.email_user, self.email_pass)
            server.send_message(msg)
            server.quit()
            
            print("✅ Email enviado")
            
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
            current_price = self.get_price(product['url'])
            is_alert = current_price and current_price <= product['target_price']
            
            if is_alert:
                total_savings += (product['target_price'] - current_price)
            
            current_data["products"].append({
                "name": product.get('name', 'Sin nombre'),
                "url": product['url'],
                "current_price": current_price,
                "target_price": product['target_price'],
                "alert": is_alert
            })
        
        current_data["total_savings"] = round(total_savings, 2)
        
        # Guardar datos actuales
        with open('docs/data/current-prices.json', 'w', encoding='utf-8') as f:
            json.dump(current_data, f, ensure_ascii=False, indent=2)
        
        # Historial
        history_file = 'docs/data/price-history.json'
        try:
            with open(history_file, 'r', encoding='utf-8') as f:
                history_data = json.load(f)
        except FileNotFoundError:
            history_data = {"history": {}}
        
        today = datetime.now().strftime('%Y-%m-%d')
        for product_data in current_data["products"]:
            if product_data["current_price"]:
                product_name = product_data["name"]
                if product_name not in history_data["history"]:
                    history_data["history"][product_name] = []
                
                today_entry = {
                    "date": today,
                    "price": product_data["current_price"]
                }
                
                existing_today = next((entry for entry in history_data["history"][product_name] 
                                     if entry["date"] == today), None)
                
                if existing_today:
                    existing_today["price"] = product_data["current_price"]
                else:
                    history_data["history"][product_name].append(today_entry)
                
                history_data["history"][product_name] = history_data["history"][product_name][-30:]
        
        with open(history_file, 'w', encoding='utf-8') as f:
            json.dump(history_data, f, ensure_ascii=False, indent=2)
        
        print("✅ Dashboard actualizado")
    
    def run(self):
        print("🔍 Iniciando monitoreo...")
        print(f"📅 {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
        print("-" * 50)
        
        config = self.load_products()
        products = config.get('products', [])
        
        if not products:
            print("❌ No hay productos en config.json")
            return
        
        alerts = []
        
        for i, product in enumerate(products, 1):
            print(f"[{i}/{len(products)}] {product.get('name', 'Sin nombre')}")
            
            current_price = self.get_price(product['url'])
            target_price = product['target_price']
            
            if current_price:
                print(f"   💰 Actual: €{current_price}")
                print(f"   🎯 Objetivo: €{target_price}")
                
                if current_price <= target_price:
                    print(f"   🎉 ¡PRECIO ALCANZADO!")
                    alerts.append({
                        'title': product.get('name', 'Producto'),
                        'current_price': current_price,
                        'target_price': target_price,
                        'url': product['url']
                    })
                else:
                    diff = current_price - target_price
                    print(f"   ⏳ Faltan €{diff:.2f}")
            else:
                print(f"   ❌ No se pudo obtener precio")
            print()
        
        # Guardar datos dashboard
        self.save_dashboard_data(products, alerts)
        
        # Enviar emails
        if alerts:
            print(f"📧 Enviando notificación para {len(alerts)} producto(s)")
            self.send_notification(alerts)
        else:
            print("😴 Sin ofertas por ahora")
        
        print("✅ Monitoreo completado")

if __name__ == "__main__":
    monitor = GitHubAmazonMonitor()
    monitor.run()