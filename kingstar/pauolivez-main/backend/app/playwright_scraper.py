import json, sys, time, requests
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium_stealth import stealth
from bs4 import BeautifulSoup
import cloudscraper
from scraper_graph import ejecutar_scraping_web
from flaresolverr_manager import start_flaresolverr
import os
from urllib.parse import urljoin

# ... (resto de funciones sin cambios) ...

def generar_prompt_inteligente(url):
    return (
        f"Analiza la página '{url}' y devuélveme un JSON con los siguientes campos:\n"
        f"- 'selectores': selectores CSS para nombre, precio y disponibilidad.\n"
        f"- 'apartados': selectores CSS de los contenedores de producto.\n"
        f"- 'click_mas': selector CSS del botón de 'siguiente página' o 'ver más', si existe.\n"
        f"- 'scroll': true si hay que hacer scroll para cargar más productos.\n"
        f"Revisa cuidadosamente si la web tiene paginación o navegación entre secciones. "
        f"Si hay múltiples páginas de productos, asegúrate de incluir el selector del botón que lleva a la siguiente.\n"
        f"Responde solo con JSON. No expliques nada más."
    )

def navegar_y_extraer(driver, url, plan):
    productos = []
    secciones_visitadas = set()

    def verificar_selectores(plan):
        try:
            html = driver.page_source
            soup = BeautifulSoup(html, 'html.parser')
            errores = []
            for key, selector in plan.get("selectores", {}).items():
                if not soup.select_one(selector):
                    errores.append((key, selector))
            if errores:
                print("[ERROR] Selectores inválidos detectados:", errores)
                with open("debug_html_sin_selectores.html", "w", encoding="utf-8") as f:
                    f.write(html)
                with open("debug_plan_erroneo.json", "w", encoding="utf-8") as f:
                    json.dump(plan, f, indent=2)
                return False
            return True
        except Exception as e:
            print("[ERROR] Fallo al verificar selectores:", e)
            return False

    def extraer_productos_en_pagina(driver, plan):
        html = driver.page_source
        soup = BeautifulSoup(html, 'html.parser')
        items = []
        contenedores = soup.select(plan['apartados'][0]) if plan.get("apartados") else soup.select(".product_pod")
        print(f"[LOG] Contenedores detectados: {len(contenedores)}")
        for c in contenedores:
            nombre = c.select_one(plan['selectores']['nombre'])
            precio = c.select_one(plan['selectores']['precio'])
            disponibilidad = c.select_one(plan['selectores']['disponibilidad'])
            items.append({
                "nombre": nombre.text.strip() if nombre else "No disponible",
                "precio": precio.text.strip() if precio else "No disponible",
                "disponibilidad": disponibilidad.text.strip() if disponibilidad else "Desconocida"
            })
        return items

    def procesar():
        if not verificar_selectores(plan):
            return

        if plan.get("scroll"):
            for _ in range(5):
                driver.execute_script("window.scrollBy(0, document.body.scrollHeight);")
                time.sleep(1)

        productos.extend(extraer_productos_en_pagina(driver, plan))

        if plan.get("click_mas"):
            while True:
                try:
                    btn = driver.find_element(By.CSS_SELECTOR, plan["click_mas"])
                    href = btn.get_attribute("href")
                    if href:
                        href = urljoin(driver.current_url, href)
                        print(f"[SCRAPER] Detectado enlace a otra página: {href}")
                        if href in secciones_visitadas:
                            break
                        secciones_visitadas.add(href)
                        driver.get(href)
                    else:
                        driver.execute_script("arguments[0].scrollIntoView();", btn)
                        time.sleep(0.5)
                        driver.execute_script("arguments[0].click();", btn)
                    print("[SCRAPER] Click en botón 'más' o navegación a nueva página")
                    time.sleep(3)
                    productos.extend(extraer_productos_en_pagina(driver, plan))
                except Exception as e:
                    print(f"[SCRAPER] Fin de botones 'más' o error: {e}")
                    break

    print(f"[SCRAPER] Navegando sección principal: {url}")
    driver.get(url)
    time.sleep(3)
    procesar()

    return productos

# ... (resto del código sin cambios) ...

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(json.dumps({"error": "URL requerida"}))
    else:
        url = sys.argv[1]
        instrucciones = generar_prompt_inteligente(url)
        resultado = ejecutar_scraping_web(url, instrucciones)
        print(json.dumps(resultado, indent=2))
