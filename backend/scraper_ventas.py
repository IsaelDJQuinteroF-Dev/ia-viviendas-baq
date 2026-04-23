import asyncio
from playwright.async_api import async_playwright
import pandas as pd

async def ejecutar_scraper():
    async with async_playwright() as p:
        print("🤖 Iniciando robot explorador...")
        browser = await p.chromium.launch(headless=False) # Lo dejamos visible para ver qué hace
        page = await browser.new_page()
        
        print("🌐 Navegando a la lista de Barranquilla...")
        await page.goto("https://www.sales.com.co/inmuebles-venta/casas-en-venta-en-barranquilla/2/todas", wait_until="networkidle")

        # Scroll para cargar todo
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await page.wait_for_timeout(3000)

        # Capturamos enlaces
        enlaces = await page.eval_on_selector_all("a[href*='/inmueble-venta/']", "nodes => nodes.map(n => n.href)")
        enlaces = list(set(enlaces)) 
        
        print(f"🏠 ¡Detectadas {len(enlaces)} casas! Entrando a investigar...")

        datos_finales = []
        for link in enlaces[:5]: # Solo 5 para probar rápido
            try:
                print(f"🔍 Revisando: {link}")
                await page.goto(link, wait_until="domcontentloaded")
                
                # ESPERA CRÍTICA: Damos tiempo a que aparezca la tabla
                await page.wait_for_timeout(5000) 

                # Extracción más robusta usando texto plano si falla el selector
                contenido = await page.content()
                if "Barrio" in contenido:
                    # Buscamos el dato que está justo después de la palabra 'Barrio'
                    barrio = await page.locator("td:right-of(td:has-text('Barrio'))").first.inner_text()
                    precio = await page.locator(".price").first.inner_text()
                    
                    resumen = {
                        "Barrio": barrio.strip(),
                        "Precio": precio.strip(),
                        "Link": link
                    }
                    datos_finales.append(resumen)
                    print(f"✅ ¡Dato capturado! Barrio: {resumen['Barrio']}")
            except Exception as e:
                print(f"⚠️ Error en esta casa: {e}")
                continue

        if datos_finales:
            df = pd.DataFrame(datos_finales)
            df.to_csv('../data/viviendas_baq.csv', index=False, encoding='utf-8')
            print(f"🏁 ¡Misión cumplida! {len(datos_finales)} registros guardados.")
        else:
            print("❌ El robot regresó con las manos vacías otra vez.")
            
        await browser.close()

if __name__ == "__main__":
    asyncio.run(ejecutar_scraper())