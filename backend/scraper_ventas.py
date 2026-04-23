import asyncio
from playwright.async_api import async_playwright
import pandas as pd

async def ejecutar_scraper():
    async with async_playwright() as p:
        print("🤖 Iniciando robot navegador (Playwright)...")
        # headless=True para que trabaje en segundo plano
        browser = await p.chromium.launch(headless=True) 
        page = await browser.new_page()
        
        url = "https://www.sales.com.co/inmuebles-venta/inmuebles-en-venta-en-barranquilla/2/todas"
        print(f"🔗 Conectando a: {url}")
        
        await page.goto(url, wait_until="networkidle")

        print("⏳ Esperando carga de datos dinámicos...")
        await page.wait_for_selector(".price:not(:has-text('{{'))")

        viviendas = []
        cards = await page.query_selector_all(".boxprod")

        for card in cards:
            try:

                precio_texto = await card.eval_on_selector(".price", "el => el.innerText")
                barrio_texto = await card.eval_on_selector("h5", "el => el.innerText")
                
                precio_limpio = precio_texto.replace('$', '').replace('.', '').replace('venta', '').strip()
                
                viviendas.append({
                    "Barrio": barrio_texto.strip(),
                    "Precio": precio_limpio
                })
            except:
                continue

        await browser.close()
        
        df = pd.DataFrame(viviendas)
        df.to_csv('../data/viviendas_baq.csv', index=False, encoding='utf-8')
        print(f"✅ ¡Éxito! Se capturaron {len(viviendas)} registros reales.")

if __name__ == "__main__":
    asyncio.run(ejecutar_scraper())