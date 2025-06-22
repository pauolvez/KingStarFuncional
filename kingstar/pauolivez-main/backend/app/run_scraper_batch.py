import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import csv
import json
import os
from scrape_script import ejecutar_scraping_una_pagina as ejecutar_scraping

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(BASE_DIR, "urls", "urls.csv")
OUTPUT_PATH = os.path.join(BASE_DIR, "urls", "resultados_scraping.json")

def main():
    resultados = []

    with open(CSV_PATH, newline='', encoding='utf-8') as csvfile:
        lector = csv.DictReader(csvfile)
        for fila in lector:
            url = fila["url"]
            instrucciones = fila["instrucciones"]
            print(f"🔍 Scrapeando: {url}")
            resultado = ejecutar_scraping(url, instrucciones)
            print(f"📄 Resultado recibido: {resultado}")
            resultado["url"] = url
            resultados.append(resultado)

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(resultados, f, indent=2, ensure_ascii=False)

    print(f"✅ Scraping terminado. Resultados guardados en {OUTPUT_PATH}")

if __name__ == "__main__":
    main()
