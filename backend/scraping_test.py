import requests
from bs4 import BeautifulSoup

# 1. Definimos la URL (usa una de un portal inmobiliario para probar)
url = 'https://www.sales.com.co/inmuebles-venta/inmuebles-en-venta-en-barranquilla/2/todas#/?precio_min=0&area_min=0&page=1&nuevos=0&destacados=0&order_by=destacados&codigo=&ciudad=2&tipo_publicacion=venta' 

# 2. Los "Headers" son vitales: le dicen al sitio que eres un navegador real y no un bot simple
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36'
}

def probar_conexion(url):
    try:
        response = requests.get(url, headers=headers, timeout=10)
        
        # Si el status es 200, todo está OK
        if response.status_code == 200:
            print(f"✅ Conexión exitosa a: {url}")
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Intentamos extraer el título de la página como prueba
            titulo = soup.title.string if soup.title else "No se encontró título"
            print(f"📌 Título de la web: {titulo}")
            
            return soup
        else:
            print(f"❌ Error: El servidor respondió con status {response.status_code}")
            return None
            
    except Exception as e:
        print(f"⚠️ Ocurrió un error: {e}")
        return None

if __name__ == "__main__":
    probar_conexion(url)