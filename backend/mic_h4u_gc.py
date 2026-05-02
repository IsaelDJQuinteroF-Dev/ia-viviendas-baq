import asyncio
from playwright.async_api import async_playwright
import pandas as pd
from datetime import datetime
import os

# ─────────────────────────────────────────────
# CONFIGURACIÓN DE SITIOS — WPResidence CMS
# Los 3 comparten estructura HTML idéntica
# ─────────────────────────────────────────────
SITIOS = [
    {
        "nombre": "MIC",
        "url_lista": (
            "https://micinmobiliaria.com/s?simple=1-4-82"
            "&simple_label=Barranquilla%2C+Atl%C3%A1ntico%2C+Colombia"
            "&id_property_type=1&id_property_condition="
            "&business_type%5B%5D=for_sale"
        ),
        "dominio": "micinmobiliaria.com",
    },
#    
#   {
#        "nombre": "HOUSE4U",
#        "url_lista": (
#            "https://house4uonline.co/s/casa/venta/atlantico/barranquilla/"
#            "?id_city=82&id_property_type=1&business_type%5B%5D=for_sale"
#        ),
#        "dominio": "house4uonline.co",
#    },

    {
        "nombre": "GC",
        "url_lista": (
            "https://gcinmobiliaria.com.co/s?id_city=82"
            "&id_location=&id_zone="
            "&id_property_type=1&id_property_condition="
            "&business_type%5B%5D=for_sale"
            "&bedrooms=&bathrooms=&min_price=&max_price="
        ),
        "dominio": "gcinmobiliaria.com.co",
    },
]

# Fase actual: solo casas residenciales
TIPOS_ACTIVOS = [
    "casa",
    # "apartamento",
    # "aparta-estudio",
]

MAX_PAGINAS   = 10   # límite páginas por sitio — quitar en producción
MAX_INMUEBLES = 50   # límite inmuebles por sitio — quitar en producción


# ─────────────────────────────────────────────
# VALIDADORES
# ─────────────────────────────────────────────
def es_estrato_valido(valor: str) -> bool:
    """Estrato residencial válido: entero entre 1 y 6."""
    try:
        return 1 <= int(str(valor).strip()) <= 6
    except (ValueError, AttributeError):
        return False


def es_tipo_activo(url: str) -> bool:
    return any(t in url.lower() for t in TIPOS_ACTIVOS)


def es_url_detalle(url: str, dominio: str) -> bool:
    """
    Filtra solo URLs de detalle de inmueble.
    Excluye: búsquedas, filtros, paginación, arriendos.
    Confirmado: URLs de detalle tienen slug tipo
    /casa-venta-barrio-ciudad/CODIGO
    """
    return (
        dominio in url
        and es_tipo_activo(url)
        and "/s?"          not in url
        and "/s/"          not in url
        and "ventas?"      not in url
        and "arriendos?"   not in url
        and "business_type" not in url
        and "id_property"  not in url
        and "page="        not in url
        and "id_city"      not in url
        and url.count("/") >= 4
    )

def parsear_tabla(items: list) -> dict:
    """
    Convierte lista ['Label: Valor', ...] en dict {'label': 'valor'}.
    Claves en minúscula para búsqueda case-insensitive.
    """
    mapa = {}
    for item in items:
        item = item.strip()
        if ":" in item:
            partes = item.split(":", 1)
            clave  = partes[0].strip().lower()
            valor  = partes[1].strip()
            mapa[clave] = valor
    return mapa


# ─────────────────────────────────────────────
# EXTRACTOR DE DETALLE — WPResidence
# ─────────────────────────────────────────────
async def extraer_detalle(page, url: str, sitio: str) -> dict | None:
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=60000)
        # Selector confirmado: ul.list-info-2
        await page.wait_for_selector("ul.list-info-2", timeout=15000)
        await page.wait_for_timeout(1000)

        # ── Tabla principal ──
        try:
            items_raw = await page.locator("ul.list-info-2 li").all_inner_texts()
            tabla = parsear_tabla(items_raw)
        except:
            tabla = {}

        def get(label: str) -> str:
            """Búsqueda parcial, case-insensitive."""
            label_lower = label.lower()
            for k, v in tabla.items():
                if label_lower in k:
                    return v
            return "N/A"

        # ── Precio ──
        try:
            precio_raw = await page.locator(
                "span.price, .price-box span, "
                "h2.price, .listing-price"
            ).first.inner_text(timeout=4000)
            precio = (precio_raw
                      .replace("$", "").replace(".", "")
                      .replace(",", "").replace("COP", "")
                      .replace("Pesos Colombianos", "")
                      .replace("Precio de venta", "")
                      .strip())
        except:
            precio = "N/A"

        # ── Características internas ──
        # WPResidence usa ul.list-info-1 para checkboxes de características
        try:
            caract_items = await page.locator(
                "ul.list-info-1 li"
            ).all_inner_texts()
            caract_raw = ", ".join([c.strip() for c in caract_items if c.strip()])
        except:
            caract_raw = "N/A"

        # ── Validar estrato ──
        estrato = get("estrato")
        if not es_estrato_valido(estrato):
            print(f"  ⏭️  Omitido (estrato '{estrato}'): {url}")
            return None

        # Barrio = Zona o Localidad (según el sitio)
        barrio = get("zona")
        if barrio == "N/A":
            barrio = get("localidad")

        cod = url.rstrip("/").split("/")[-1]

        return {
            "fecha_extraccion":  datetime.now().strftime("%Y-%m-%d"),
            "fuente":            sitio,
            "cod_inmueble":      cod,
            "tipo_inmueble":     "casa",
            "ciudad":            get("ciudad"),
            "barrio":            barrio,
            "estrato":           int(estrato.strip()),
            "habitaciones":      get("alcobas"),
            "banos":             get("baños"),
            "area_construida":   get("área construida"),
            "area_terreno":      get("área terreno"),
            "area_privada":      get("área privada"),
            "garaje":            get("garaje"),
            "piso":              get("piso"),
            "anio_construccion": get("año construcción"),
            "estado":            get("estado"),
            "tipo_negocio":      get("tipo de negocio"),
            "caract_internas":   caract_raw,
            "precio_cop":        precio,
            "url":               url,
        }

    except Exception as e:
        print(f"  ⚠️  Error en {url}: {e}")
        return None


# ─────────────────────────────────────────────
# SCRAPER DE UN SITIO — con paginación
# ─────────────────────────────────────────────
async def scraper_sitio(page, sitio: dict) -> list:
    nombre    = sitio["nombre"]
    url_lista = sitio["url_lista"]
    dominio   = sitio["dominio"]

    print(f"\n{'='*50}")
    print(f"🏢 Iniciando {nombre}")
    print(f"{'='*50}")

    datos            = []
    pagina           = 1
    total_procesados = 0

    while pagina <= MAX_PAGINAS and total_procesados < MAX_INMUEBLES:

        # Paginación WPResidence: &page=N
        sep     = "&" if "?" in url_lista else "?"
        url_pag = f"{url_lista}{sep}page={pagina}" if pagina > 1 else url_lista

        print(f"\n📄 [{nombre}] Página {pagina}")
        try:
            await page.goto(url_pag, wait_until="domcontentloaded", timeout=60000)
            await page.wait_for_timeout(3000)
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await page.wait_for_timeout(2000)
        except Exception as e:
            print(f"⚠️  No se pudo cargar página {pagina}: {e}")
            break

        # Extraer todos los href y filtrar solo detalle
        try:
            todos_links = await page.eval_on_selector_all(
                "a[href]",
                "nodes => [...new Set(nodes.map(n => n.href))]"
            )
            enlaces = [l for l in todos_links if es_url_detalle(l, dominio)]
        except Exception as e:
            print(f"⚠️  Error extrayendo enlaces: {e}")
            break

        if not enlaces:
            print(f"ℹ️  Sin inmuebles en página {pagina} — fin de {nombre}")
            break

        print(f"🏠 {len(enlaces)} casas en página {pagina}")

        for link in enlaces:
            if total_procesados >= MAX_INMUEBLES:
                break
            print(f"  🔎 [{total_procesados + 1}] {link}")
            resultado = await extraer_detalle(page, link, nombre)
            if resultado:
                datos.append(resultado)
                total_procesados += 1
                print(
                    f"  ✅ {nombre} | Barrio: {resultado['barrio']} | "
                    f"${resultado['precio_cop']} | "
                    f"{resultado['area_construida']} | "
                    f"Estrato: {resultado['estrato']}"
                )
            await asyncio.sleep(1)

        pagina += 1

    print(f"\n✅ {nombre} completado — {len(datos)} registros")
    return datos


# ─────────────────────────────────────────────
# ORQUESTADOR PRINCIPAL
# ─────────────────────────────────────────────
async def ejecutar_scraper():
    async with async_playwright() as p:
        print("🤖 Iniciando scraper MIC + House4u + GC")
        browser = await p.chromium.launch(headless=False)
        page    = await browser.new_page()

        todos_los_datos = []

        for sitio in SITIOS:
            try:
                datos_sitio = await scraper_sitio(page, sitio)
                todos_los_datos.extend(datos_sitio)
            except Exception as e:
                print(f"❌ Error crítico en {sitio['nombre']}: {e}")
                continue

        await browser.close()

        if not todos_los_datos:
            print("❌ No se obtuvieron registros.")
            return

        df_nuevo = pd.DataFrame(todos_los_datos)

        # ── CSV acumulativo — nunca sobreescribe ──
        ruta_csv = "../data/viviendas_baq.csv"
        if os.path.exists(ruta_csv):
            df_existente = pd.read_csv(ruta_csv, encoding="utf-8")
            df_total     = pd.concat([df_existente, df_nuevo], ignore_index=True)
            df_total     = df_total.drop_duplicates(
                subset=["url", "fecha_extraccion"], keep="last"
            )
        else:
            df_total = df_nuevo

        df_total.to_csv(ruta_csv, index=False, encoding="utf-8")

        print(f"\n{'='*50}")
        print(f"🏆 MISIÓN CUMPLIDA")
        print(f"   Nuevos registros : {len(df_nuevo)}")
        print(f"   Total en CSV     : {len(df_total)}")
        print(f"{'='*50}")
        print(df_nuevo[["fuente", "barrio", "precio_cop",
                         "area_construida", "estrato"]].to_string())


if __name__ == "__main__":
    asyncio.run(ejecutar_scraper())