import asyncio
from playwright.async_api import async_playwright
import pandas as pd
from datetime import datetime

''' 
─────────────────────────────────────────────
CONFIGURACIÓN DE TIPOS DE INMUEBLE
 Tipos residenciales: 'apartamento', 'aparta-estudio', 'loft', 'penthouse'
 Tipos mixtos:        'lote', 'finca', 'casa-campo'
 Tipos comerciales:   'oficina', 'local', 'bodega' (excluidos por ahora)
─────────────────────────────────────────────
'''
TIPOS_ACTIVOS = [
    'casa'
]

def es_tipo_activo(url: str) -> bool:
    """Filtra URLs según los tipos de inmueble habilitados."""
    return any(tipo in url.lower() for tipo in TIPOS_ACTIVOS)


async def ejecutar_scraper():
    async with async_playwright() as p:
        print("🤖 Iniciando robot explorador...")
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()

        print("🌐 Navegando a la lista de Barranquilla...")
        await page.goto(
            "https://www.sales.com.co/inmuebles-venta/casas-en-venta-en-barranquilla/2/todas",
            wait_until="networkidle"
        )

        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await page.wait_for_timeout(3000)

        todos_los_enlaces = await page.eval_on_selector_all(
            "a[href*='/inmueble-venta/']",
            "nodes => nodes.map(n => n.href)"
        )

        # Aplica filtro de tipos activos + elimina duplicados
        enlaces = list(set([e for e in todos_los_enlaces if es_tipo_activo(e)]))

        print(f"🏠 {len(enlaces)} inmuebles detectados | Tipos activos: {TIPOS_ACTIVOS}")

        datos_finales = []

        for i, link in enumerate(enlaces):
            try:
                print(f"🔎 [{i+1}/{len(enlaces)}] {link}")
                await page.goto(link, wait_until="networkidle", timeout=60000)
                await page.wait_for_selector(".table-responsive", timeout=10000)

                async def extraer_campo(label):
                    try:
                        return await page.locator(
                            f"tr:has(h4:text('{label}')) td:nth-child(2)"
                        ).inner_text(timeout=3000)
                    except:
                        return "N/A"

                try:
                    precio_raw = await page.locator(".price").first.inner_text()
                    precio = precio_raw.replace('$','').replace('.','').replace('venta','').strip()
                except:
                    precio = "N/A"

                # Tipo de inmueble extraído de la URL para trazabilidad
                tipo_detectado = next(
                    (t for t in TIPOS_ACTIVOS if t in link.lower()), "otro"
                )

                resumen = {
                    "fecha_extraccion": datetime.now().strftime("%Y-%m-%d"),
                    "tipo_inmueble":    tipo_detectado,
                    "barrio":           await extraer_campo("Barrio"),
                    "estrato":          await extraer_campo("Estrato"),
                    "area_m2":          await extraer_campo("Área:"),
                    "habitaciones":     await extraer_campo("Habitaciones"),
                    "banos":            await extraer_campo("Baños"),
                    "garaje":           await extraer_campo("Garaje"),
                    "precio_cop":       precio,
                    "url":              link
                }

                datos_finales.append(resumen)
                print(f"✅ {resumen['tipo_inmueble'].upper()} | "
                      f"Barrio: {resumen['barrio']} | "
                      f"${resumen['precio_cop']} | "
                      f"{resumen['area_m2']} m²")

                await asyncio.sleep(1)

            except Exception as e:
                print(f"⚠️  Error en {link}: {e}")
                continue

        await browser.close()

        if datos_finales:
            df = pd.DataFrame(datos_finales)
            df.to_csv('../data/viviendas_baq.csv', index=False, encoding='utf-8')
            print(f"\n🏆 ¡Misión cumplida! {len(datos_finales)} registros en viviendas_baq.csv")
            print(df.head())
        else:
            print("❌ No se guardaron registros.")


if __name__ == "__main__":
    asyncio.run(ejecutar_scraper())