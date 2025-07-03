import json
import os
import csv

PLANS_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "static_scraping_plans.json")
)

OUTPUT_CSV = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "urls", "urls.csv")
)

def cargar_planes():
    with open(PLANS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def generar_urls(base_url, paginador, total_paginas):
    urls = []
    tipo = paginador["tipo"]
    formato = paginador.get("formato", "")
    incremento = paginador.get("incremento", 1)
    inicio_en = paginador.get("inicio_en", 2)

    # Página base (sin paginación explícita)
    urls.append(base_url)

    # Generar páginas paginadas (desde inicio_en hasta total_paginas)
    for i in range(1, total_paginas):
        if tipo == "offset":
            offset = i * incremento
            sep = "&" if "?" in base_url else "?"
            urls.append(base_url + sep + formato.replace("{OFFSET}", str(offset)))
        elif tipo == "path_num":
            numero = i + inicio_en - 1
            if base_url.endswith("/"):
                base_url = base_url[:-1]
            urls.append(f"{base_url}{formato.replace('{NUM}', str(numero))}")
        elif tipo == "query_param":
            numero = i + inicio_en - 1
            if "?" in base_url:
                base, existing_query = base_url.split("?", 1)
                # Añadir &SDM=list para FNAC
                new_query = f"PageIndex={numero}&{existing_query}&SDM=list"
                urls.append(f"{base}?{new_query}")
            else:
                # Asegurarse de agregar &SDM=list en la URL
                urls.append(f"{base_url}?PageIndex={numero}&SDM=list")
        else:
            print("❌ Tipo de paginador no soportado.")
            return []

    return urls


def main():
    planes = cargar_planes()
    dominios = list(planes.keys())

    print("Selecciona la web:")
    for idx, dominio in enumerate(dominios, 1):
        print(f"{idx}. {dominio}")
    opcion = int(input("Número de la web: ")) - 1
    dominio = dominios[opcion]

    base_url = input("👉 Pega la URL base de la sección: ").strip()
    paginas = int(input("📄 ¿Cuántas páginas tiene esa sección?: "))

    plan = planes[dominio]
    paginador = plan.get("paginador")
    if not paginador:
        print("❌ Esta web no tiene configurado un bloque de paginador en static_scraping_plans.json")
        return

    urls = generar_urls(base_url, paginador, paginas)
    if not urls:
        return

    with open(OUTPUT_CSV, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        for url in urls:
            writer.writerow([url, "Extrae todos los productos"])

    print(f"✅ Se añadieron {len(urls)} URLs al archivo {OUTPUT_CSV}")

if __name__ == "__main__":
    main()
