from fastapi import APIRouter, HTTPException
import csv
import json
import os
import subprocess
from pathlib import Path
from datetime import datetime

router = APIRouter()

CSV_PATH = os.path.join("app", "urls", "urls.csv")
OUTPUT_PATH = os.path.join("app", "urls", "resultados_scraping.json")
PLANS_PATH = os.path.join("app", "static_scraping_plans.json")


@router.get("/scrap-todas-las-urls")
def scrap_todas():
    ruta_script = Path(__file__).parent / "run_scraper_batch.py"
    if not ruta_script.exists():
        raise HTTPException(status_code=500, detail="No se encontró run_scraper_batch.py")

    try:
        subprocess.run(["python", str(ruta_script)], check=True)
        return {
            "mensaje": "✅ Scraping lanzado correctamente usando subprocess.",
            "archivo": str(OUTPUT_PATH)
        }
    except subprocess.CalledProcessError as e:
        raise HTTPException(status_code=500, detail=f"❌ Error al ejecutar el scraper: {e}")


@router.post("/generar-urls")
def generar_urls(
    dominio: str,
    url_base: str,
    paginas: int
):
    if not os.path.exists(PLANS_PATH):
        raise HTTPException(status_code=404, detail="No existe static_scraping_plans.json")

    with open(PLANS_PATH, "r", encoding="utf-8") as f:
        planes = json.load(f)

    if dominio not in planes:
        raise HTTPException(status_code=404, detail=f"No hay plan para {dominio}")

    plan = planes[dominio]
    paginador = plan.get("paginador")
    if not paginador:
        raise HTTPException(status_code=400, detail=f"{dominio} no tiene bloque 'paginador'")

    tipo = paginador.get("tipo")
    formato = paginador.get("formato", "")
    incremento = paginador.get("incremento", 1)
    inicio_en = paginador.get("inicio_en", 1)

    urls = []
    for i in range(paginas):
        if tipo == "offset":
            offset = i * incremento
            if offset == 0:
                urls.append(url_base)
            else:
                sep = "&" if "?" in url_base else "?"
                urls.append(f"{url_base}{sep}{formato.replace('{OFFSET}', str(offset))}")
        elif tipo == "path_num":
            num = i + inicio_en
            if i == 0 and inicio_en == 1:
                urls.append(url_base)
            else:
                urls.append(f"{url_base}{formato.replace('{NUM}', str(num))}")
        else:
            raise HTTPException(status_code=400, detail="Tipo de paginador no soportado")

    with open(CSV_PATH, "a", newline='', encoding="utf-8") as f:
        writer = csv.writer(f)
        for url in urls:
            writer.writerow([url, "Extrae todos los productos"])

    return {
        "mensaje": f"{len(urls)} URLs añadidas correctamente a urls.csv",
        "urls": urls
    }
