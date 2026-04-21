import requests
from bs4 import BeautifulSoup
import pandas as pd
import time

base_url = "https://www.sales.com.co/inmuebles-venta/inmuebles-en-venta-en-barranquilla/2/todas#/?precio_min=0&area_min=0&nuevos=0&destacados=0&order_by=destacados&codigo=&ciudad=2&tipo_publicacion=venta&page="
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36'}

def scrape_multiples_paginas(total_paginas):
    todas_las_viviendas = []
    
    for i in range(1, total_paginas + 1):
        print(f"📄 Procesando página {i}...")
        url_actual = f"{base_url}{i}"
        
        try:
            response = requests.get(url_actual, headers=headers, timeout=15)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                cards = soup.find_all('div', class_='boxprod') # La clase que identificaste
                
                if not cards:
                    print(f"⚠️ No se detectaron tarjetas en la página {i}. Deteniendo...")
                    break
                
                for card in cards:
                    try:
                        precio = card.find('span', class_='price').get_text(strip=True)
                        barrio = card.find('h5').get_text(strip=True) if card.find('h5') else "Desconocido"
                        
                        todas_las_viviendas.append({
                            'Barrio': barrio,
                            'Precio': precio.replace('$', '').replace('.', '').replace('venta', '').strip()
                        })
                    except:
                        continue
                
                time.sleep(2) 
            else:
                print(f"❌ Error en página {i}: Status {response.status_code}")
        except Exception as e:
            print(f"⚠️ Error inesperado: {e}")
            break

    if todas_las_viviendas:
        df = pd.DataFrame(todas_las_viviendas)
        df.to_csv('../data/viviendas_baq_full.csv', index=False, encoding='utf-8')
        print(f"✅ ¡Éxito! Se recolectaron {len(todas_las_viviendas)} registros en viviendas_baq_full.csv")

if __name__ == "__main__":

    scrape_multiples_paginas(total_paginas=5)