import asyncio
from playwright.async_api import async_playwright
import pandas as pd
from datetime import datetime

'''
 ─────────────────────────────────────────────
 CONFIGURACIÓN DE TIPOS DE INMUEBLE
 Fase actual: solo 'casa'
 ─────────────────────────────────────────────
'''
TIPOS_ACTIVOS = [
    'casa',
]

def es_tipo_activo(url: str) -> bool:
    return any(tipo in url.lower() for tipo in TIPOS_ACTIVOS)


def parsear_otras_caracteristicas(items: list) -> dict:

    resultado = {
        "garaje":    "N/A",
        "pisos":     "N/A",
        "otras_raw": ", ".join(items)  # guardamos todo como respaldo
    }
    for item in items:
        item_up = item.upper()
        if "GARAJE" in item_up:
            resultado["garaje"] = item.strip()
        elif "PISO" in item_up:
            resultado["pisos"] = item.strip()
    return resultado

def es_estrato_valido(estrato: str) -> bool:
    try:
        return 1 <= int(estrato.strip()) <= 6
    except (ValueError, AttributeError):
        return False

async def ejecutar_scraper():
    async with async_playwright() as p:
        print("🤖 Iniciando robot explorador...")
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()

        print("🌐 Navegando a la lista de Barranquilla...")
        await page.goto(
            "https://www.sales.com.co/inmuebles-venta/casa-en-venta-en-barranquilla/2/1",
            wait_until="networkidle",
            timeout=60000
        )
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await page.wait_for_timeout(3000)

        todos_los_enlaces = await page.eval_on_selector_all(
            "a[href*='/inmueble-venta/']",
            "nodes => nodes.map(n => n.href)"
        )
        enlaces_casas = list(set([e for e in todos_los_enlaces if es_tipo_activo(e)]))

        if not enlaces_casas:
            print("❌ No se encontraron casas en la lista.")
            await browser.close()
            return

        print(f"🏠 {len(enlaces_casas)} casas en página 1. Iniciando navegación por 'Siguiente'...")

        await page.goto(enlaces_casas[0], wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_timeout(3000)

        datos_finales = []
        procesados = 0
        MAX_INMUEBLES = 50  # límite para fase de prueba — quitar en producción

        while procesados < MAX_INMUEBLES:
            try:
                await page.wait_for_selector(".table-responsive", timeout=15000)

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

                url_actual = page.url
                cod = url_actual.rstrip('/').split('/')[-1]

                tipo_detectado = next(
                    (t for t in TIPOS_ACTIVOS if t in url_actual.lower()), "otro"
                )

                try:
                    items_otras = await page.locator(
                        "div.otras-caracteristicas div.caracteristicas-detalle ul li"
                    ).all_inner_texts()
                except:
                    items_otras = []

                otras = parsear_otras_caracteristicas(items_otras)

                estrato_raw = await extraer_campo("Estrato")

                if not es_estrato_valido(estrato_raw):
                    print(f"⏭️  Omitido (estrato '{estrato_raw}'): {page.url}")
                    try:
                        await page.locator("a:has-text('Siguiente')").click()
                        await page.wait_for_selector(".table-responsive", timeout=20000)
                    except:
                        break
                    continue
 
                resumen = {
                    "fecha_extraccion": datetime.now().strftime("%Y-%m-%d"),
                    "cod_inmueble":     cod,
                    "tipo_inmueble":    tipo_detectado,
                    "ciudad":           await extraer_campo("Ciudad"),
                    "barrio":           await extraer_campo("Barrio"),
                    "estrato":          int(estrato_raw.strip()),
                    "habitaciones":     await extraer_campo("Habitaciones"),
                    "banos":            await extraer_campo("Baños"),
                    "area_m2":          await extraer_campo("Área:"),
                    "garaje":           otras["garaje"],
                    "pisos":            otras["pisos"],
                    "otras_raw":        otras["otras_raw"],
                    "precio_cop":       precio,
                    "url":              url_actual
                }

                datos_finales.append(resumen)
                procesados += 1
                print(f"✅ [{procesados}] {resumen['tipo_inmueble'].upper()} | "
                      f"Cod: {cod} | Barrio: {resumen['barrio']} | "
                      f"${resumen['precio_cop']} | {resumen['area_m2']} | "
                      f"Garaje: {resumen['garaje']}")

                try:
                    siguiente = page.locator("a:has-text('Siguiente')")
                    if await siguiente.count() > 0:
                        await siguiente.click()

                        await page.wait_for_selector(".table-responsive", timeout=20000)
                        await asyncio.sleep(1)
                    else:
                        print("ℹ️ No hay más inmuebles (fin de la lista).")
                        break
                except Exception as e:
                    print(f"⚠️ No pude navegar al siguiente: {e}")
                    break

            except Exception as e:
                print(f"⚠️ Error extrayendo datos: {e}")

                try:
                    await page.locator("a:has-text('Siguiente')").click()
                    await page.wait_for_selector(".table-responsive", timeout=20000)
                    await asyncio.sleep(1)
                except:
                    break

        await browser.close()

        if datos_finales:
            df = pd.DataFrame(datos_finales)
            df.to_csv('../data/viviendas_baq.csv', index=False, encoding='utf-8')
            print(f"\n🏆 Misión cumplida — {len(datos_finales)} registros en viviendas_baq.csv")
            print(df[['barrio','precio_cop','area_m2','garaje','pisos']].head(10))
        else:
            print("❌ No se guardaron registros.")


if __name__ == "__main__":
    asyncio.run(ejecutar_scraper())