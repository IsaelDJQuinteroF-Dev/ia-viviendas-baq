🏠 ia-viviendas-baq
Valoración Inteligente de Inmuebles — Barranquilla, Colombia
> Pipeline completo: Web Scraping → ETL → Machine Learning → Predicción de valor de inmuebles residenciales en Barranquilla.
![Python](https://img.shields.io/badge/Python-3.10+-blue) ![Estado](https://img.shields.io/badge/Estado-En%20desarrollo-yellow) ![Licencia](https://img.shields.io/badge/Licencia-MIT-green)
---
¿Qué hace este proyecto?
Permite estimar el valor de mercado de un inmueble residencial en Barranquilla a partir de sus características físicas y de ubicación. El usuario ingresa los datos de la propiedad y el modelo devuelve una valoración basada en precios reales del mercado local.
---
Arquitectura del pipeline
```
[Inmobiliarias BAQ]
        ↓
  Web Scraping (Python)
        ↓
  ETL — Limpieza y normalización (pandas)
        ↓
  Base de datos (PostgreSQL)
        ↓
  Modelo ML — Entrenamiento y predicción
        ↓
  Interfaz de consulta — El usuario ingresa datos → obtiene valoración
```
---
Fuentes de datos
Datos extraídos de 8 inmobiliarias reales de Barranquilla:
Inmobiliaria	URL
Sales Inmobiliaria	https://www.sales.com.co/
Aliados Inmobiliarios	https://www.aliadosinmobiliariossa.com/
Issa Saieh Inmobiliaria	https://issasaieh.com/
MIC Inmobiliaria	https://micinmobiliaria.com/
House 4 u	http://www.house4uonline.co/
GC Inmobiliaria	https://gcinmobiliaria.com.co/
Inmobiliaria Mchaileh	https://mchaileh.com/
Inurbanas	https://inurbanas.co/
---
Variables del modelo
Variable	Descripción
`tipo_vivienda`	Casa, apartamento, etc.
`ciudad`	Barranquilla y área metropolitana
`barrio`	Sector / urbanización
`area_construida`	Metros cuadrados construidos
`area_total`	Metros cuadrados totales del lote
`habitaciones`	Número de habitaciones
`baños`	Número de baños
`garage`	Garaje incluido (sí/no)
`estrato`	Estrato socioeconómico (1–6)
`valor`	Precio de mercado (variable objetivo)
---
Stack tecnológico
Scraping: Python · BeautifulSoup · Playwright · HTTPX
ETL: pandas · numpy
Almacenamiento: PostgreSQL
Modelo: scikit-learn (en desarrollo)
Validación: detección de duplicados, outliers y anomalías de precio
---
Estado del proyecto
Componente	Estado
Scraper multi-fuente	✅ Funcional
Pipeline ETL	✅ Funcional
Base de datos PostgreSQL	🔄 En integración
Modelo ML de valoración	🔄 En desarrollo
Interfaz de consulta	🔄 Pendiente
Estimado MVP funcional	Mayo 2026
---
Uso (próximamente)
```bash
git clone https://github.com/IsaelDJQuinteroF-Dev/ia-viviendas-baq.git
cd ia-viviendas-baq
pip install -r requirements.txt
python scraper.py        # Extrae datos de inmobiliarias
python etl.py            # Limpia y normaliza
python modelo.py         # Entrena y predice
```
---
Autor
Isael De Jesús Quintero Fuentes  
Data Analyst & Python Developer | QuinCon TIC  
Barranquilla, Colombia  
LinkedIn · GitHub
---
> *Proyecto desarrollado sobre datos reales del mercado inmobiliario de Barranquilla. No afiliado a ninguna de las inmobiliarias listadas.*
