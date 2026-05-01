import asyncio
import re
from playwright.async_api import async_playwright
import pandas as pd
from datetime import datetime
import os

# ─────────────────────────────────────────────
# CONFIGURACIÓN
# House4U — Next.js/Tailwind
# Paginación: botón Siguiente, 5 items/página
# Estructura confirmada en inspector HTML
# ─────────────────────────────────────────────
URL_LISTA = "https://app.house4uonline.co/?operation=Venta&q=barranquilla"
DOMINIO   = "app.house4uonline.co"

# Fase actual: solo casas residenciales
# Excluir: casa-campestre, casa-comercial
TIPOS_ACTIVOS = ["casa"]
TIPOS_EXCLUIR = ["casa-campestre", "casa-comercial", "apartaestudio",
                 "apartamento", "local", "oficina", "bodega", "lote"]


# ─────────────────────────────────────────────
# VALIDADORES
# ─────────────────────────────────────────────
def es_casa_valida(url: str) -> bool:
    """
    Filtra URLs de detalle de casas residenciales.
    Confirma: dominio correcto + /sales/ + --CODIGO
    Excluye: tipos no residenciales por slug
    """
    if DOMINIO not in url or "/sales/" not in url or "--" not in url:
        return False
    slug = url.split("/sales/")[1].split("--")[0].lower()
    # Debe contener 'casa'
    if not any(t in slug for t in TIPOS_ACTIVOS):
        return False
    # No debe contener tipos excluidos
    if any(t in slug for t in TIPOS_EXCLUIR):
        return False
    return True


def es_estrato_valido(valor: str) -> bool:
    """Estrato residencial: int 1-6. House4U puede no tener estrato — no descarta."""
    try:
        return 1 <= int(str(valor).strip()) <= 6
    except (ValueError, AttributeError):
        return False


# ─────────────────────────────────────────────
# RECOLECTOR DE ENLACES — con filtro Barranquilla
# Estructura del listado:
#   a[href="/sales/..."]  → tarjeta de inmueble
#   span → "Barranquilla, Atlántico" o "Sabanagrande, Atlántico"
#   ← filtrar solo Barranquilla ANTES de entrar al detalle
# ─────────────────────────────────────────────
async def recolectar_enlaces(page) -> list:
    """
    Recorre todas las páginas del listado.
    Filtra casas de Barranquilla directamente en la tarjeta.
    Retorna lista de URLs únicas.
    """
    todos_enlaces = set()  # set elimina duplicados automáticamente
    pagina = 1

    # Obtener total de páginas
    try:
        total_texto = await page.locator(
            "span.text-sm.font-medium"
        ).first.inner_text(timeout=5000)
        # Formato: "1 de 41"
        total_paginas = int(total_texto.strip().split("de")[-1].strip())
    except:
        total_paginas = 50  # fallback
        print("⚠️  No se pudo leer total páginas, usando fallback 50")

    print(f"📊 Total páginas: {total_paginas}")

    while pagina <= total_paginas:
        print(f"📄 Recolectando página {pagina}/{total_paginas}...")
        await page.wait_for_timeout(2000)

        # Obtener todas las tarjetas de inmueble
        # Cada tarjeta: <a href="/sales/..."> con span de ubicación dentro
        try:
            tarjetas = await page.locator("a[href*='/sales/']").all()
            for tarjeta in tarjetas:
                href = await tarjeta.get_attribute("href")
                if not href:
                    continue
                url_completa = (
                    href if href.startswith("http")
                    else f"https://{DOMINIO}{href}"
                )
                # Filtrar tipo antes de verificar ciudad
                if not es_casa_valida(url_completa):
                    continue
                # Verificar que la ubicación en la tarjeta sea Barranquilla
                try:
                    ubicacion_span = tarjeta.locator("span").filter(
                        has_text="Barranquilla"
                    )
                    if await ubicacion_span.count() > 0:
                        todos_enlaces.add(url_completa)
                except:
                    # Si no podemos leer la ubicación, incluimos por seguridad
                    todos_enlaces.add(url_completa)
        except Exception as e:
            print(f"⚠️  Error en página {pagina}: {e}")

        casas_acum = len(todos_enlaces)
        print(f"   Casas Barranquilla acumuladas: {casas_acum}")

        # Navegar a siguiente página
        if pagina < total_paginas:
            try:
                btn = page.locator("button:has(span:text('Siguiente'))")
                if await btn.count() > 0:
                    disabled = await btn.get_attribute("disabled")
                    if disabled is not None:
                        print("ℹ️  Botón Siguiente deshabilitado — fin del listado")
                        break
                    await btn.click()
                    await page.wait_for_timeout(2500)
                else:
                    print("ℹ️  No hay botón Siguiente")
                    break
            except Exception as e:
                print(f"⚠️  Error navegando: {e}")
                break
        pagina += 1

    return list(todos_enlaces)


# ─────────────────────────────────────────────
# EXTRACTOR DE DETALLE — selectores confirmados
#
# Precio:  div.text-3xl o div[class*="text-primary"]
# Specs:   span.text-sm (label) +
#          p.text-base.font-medium.text-muted-foreground (valor)
# ─────────────────────────────────────────────
async def extraer_detalle(page, url: str) -> dict | None:
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_selector("h1", timeout=15000)
        await page.wait_for_timeout(1500)

        # ── Título ──
        try:
            titulo = (await page.locator("h1").first.inner_text()).strip()
        except:
            titulo = "N/A"

        # ── Precio — confirmado: div.text-3xl con $&nbsp; ──
        precio = "N/A"
        try:
            precio_raw = await page.locator(
                "div.text-3xl, div.text-\\[40px\\]"
            ).first.inner_text(timeout=4000)
            precio = (precio_raw
                      .replace("$", "").replace("\u00a0", "")
                      .replace(".", "").replace(",", "")
                      .replace("COP", "").strip())
            if not any(c.isdigit() for c in precio):
                precio = "N/A"
        except:
            pass

        # ── Specs — estructura confirmada: span.text-sm + p siguiente ──
        # <span class="text-sm">Habitaciones</span>
        # <p class="text-base font-medium text-muted-foreground ...">3</p>
        specs = {}
        CAMPOS = {
            "Habitaciones":       "habitaciones",
            "Baños":              "banos",
            "Garajes":            "garaje",
            "Piso":               "piso",
            "Área Privada":       "area_privada",
            "Estrato":            "estrato",
            "Año de construcción":"anio_construccion",
        }
        for label, clave in CAMPOS.items():
            try:
                # Selector: span con text exacto, luego el p hermano siguiente
                elem = page.locator(
                    f'span.text-sm:text-is("{label}")'
                )
                if await elem.count() > 0:
                    # El valor está en el p que sigue (siguiente hermano)
                    contenedor = elem.locator("xpath=../..")
                    valor_p = contenedor.locator(
                        "p.text-base"
                    ).first
                    texto = await valor_p.inner_text(timeout=3000)
                    # Año de construcción incluye "(17 años)" — extraer solo el año
                    if clave == "anio_construccion":
                        match = re.search(r'(\d{4})', texto)
                        texto = match.group(1) if match else texto
                    specs[clave] = texto.strip()
                else:
                    specs[clave] = "N/A"
            except:
                specs[clave] = "N/A"

        # ── Barrio desde URL ──
        try:
            slug = url.split("/sales/")[1].split("--")[0]
            for prefijo in [
                "casa-en-conjunto-en-", "casa-en-venta-en-",
                "casa-en-venta-", "casa-en-"
            ]:
                slug = slug.replace(prefijo, "")
            for sufijo in ["-barranquilla", "-atlantico", "-colombia"]:
                slug = slug.split(sufijo)[0]
            barrio_url = slug.replace("-", " ").title()
        except:
            barrio_url = "N/A"

        # ── Estrato: no descartar si es N/A (House4U no siempre lo publica) ──
        estrato = specs.get("estrato", "N/A")

        cod = url.rstrip("/").split("--")[-1]

        return {
            "fecha_extraccion":  datetime.now().strftime("%Y-%m-%d"),
            "fuente":            "HOUSE4U",
            "cod_inmueble":      cod,
            "tipo_inmueble":     "casa",
            "ciudad":            "Barranquilla",
            "barrio":            barrio_url,
            "estrato":           estrato,
            "habitaciones":      specs.get("habitaciones", "N/A"),
            "banos":             specs.get("banos", "N/A"),
            "area_construida":   specs.get("area_privada", "N/A"),
            "area_terreno":      "N/A",
            "area_privada":      specs.get("area_privada", "N/A"),
            "garaje":            specs.get("garaje", "N/A"),
            "piso":              specs.get("piso", "N/A"),
            "anio_construccion": specs.get("anio_construccion", "N/A"),
            "estado":            "N/A",
            "tipo_negocio":      "Venta",
            "caract_internas":   "N/A",
            "precio_cop":        precio,
            "url":               url,
        }

    except Exception as e:
        print(f"  ⚠️  Error en {url}: {e}")
        return None


# ─────────────────────────────────────────────
# ORQUESTADOR PRINCIPAL
# Estrategia: 1 página para lista + 1 página por detalle
# Evita el problema de volver al listado y re-navegar
# ─────────────────────────────────────────────
async def ejecutar_scraper():
    async with async_playwright() as p:
        print("🤖 Iniciando scraper House4U")
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()

        # PASO 1 — Recolectar todos los enlaces (una sola pasada por el listado)
        page_lista = await context.new_page()
        print("🌐 Cargando listado...")
        await page_lista.goto(
            URL_LISTA, wait_until="domcontentloaded", timeout=60000
        )
        await page_lista.wait_for_timeout(3000)

        print("\n📋 Fase 1: Recolectando enlaces...")
        todos_enlaces = await recolectar_enlaces(page_lista)
        await page_lista.close()

        print(f"\n✅ Total casas Barranquilla encontradas: {len(todos_enlaces)}")

        # PASO 2 — Extraer detalle de cada enlace
        print("\n🔍 Fase 2: Extrayendo detalles...")
        datos = []
        page_det = await context.new_page()

        for idx, link in enumerate(todos_enlaces, 1):
            print(f"  [{idx}/{len(todos_enlaces)}] {link}")
            resultado = await extraer_detalle(page_det, link)
            if resultado:
                datos.append(resultado)
                print(
                    f"  ✅ Barrio: {resultado['barrio']} | "
                    f"${resultado['precio_cop']} | "
                    f"Hab: {resultado['habitaciones']} | "
                    f"Estrato: {resultado['estrato']}"
                )
            else:
                print(f"  ❌ Sin datos")
            await asyncio.sleep(1)

        await page_det.close()
        await browser.close()

        # PASO 3 — Guardar CSV acumulativo
        if not datos:
            print("❌ No se obtuvieron registros.")
            return

        df_nuevo = pd.DataFrame(datos)
        ruta_csv = "../data/viviendas_baq.csv"

        if os.path.exists(ruta_csv):
            df_existente = pd.read_csv(ruta_csv, encoding="utf-8")
            df_total = pd.concat([df_existente, df_nuevo], ignore_index=True)
            df_total = df_total.drop_duplicates(
                subset=["url", "fecha_extraccion"], keep="last"
            )
        else:
            df_total = df_nuevo

        df_total.to_csv(ruta_csv, index=False, encoding="utf-8")

        print(f"\n{'='*50}")
        print(f"🏆 HOUSE4U — MISIÓN CUMPLIDA")
        print(f"   Nuevos registros : {len(df_nuevo)}")
        print(f"   Total en CSV     : {len(df_total)}")
        print(f"{'='*50}")
        print(df_nuevo[[
            "barrio", "precio_cop", "habitaciones",
            "estrato", "area_privada"
        ]].to_string())


if __name__ == "__main__":
    asyncio.run(ejecutar_scraper())
