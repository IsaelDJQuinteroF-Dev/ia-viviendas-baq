import asyncio
from playwright.async_api import async_playwright

async def prueba_directa():
    async with async_playwright() as p:
        print("🤖 Iniciando prueba directa...")
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        # Probamos con el link de tu captura
        await page.goto("https://www.sales.com.co/inmueble-venta/casa-en-venta-en-barranquilla/17161")
        
        # Esperamos a que la tabla sea visible
        await page.wait_for_selector(".table-responsive", timeout=10000)
        
        # Intentamos leer el Barrio Prado Mar que vimos en tu captura
        barrio = await page.locator("tr:has(h4:text('Barrio')) td:nth-child(2)").inner_text()
        print(f"🏠 El robot leyó exitosamente el barrio: {barrio}")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(prueba_directa())