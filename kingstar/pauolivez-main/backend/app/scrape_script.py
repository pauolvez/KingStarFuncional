import json, sys, time, requests, os
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium_stealth import stealth
from bs4 import BeautifulSoup
import cloudscraper
from urllib.parse import urlparse
from app.scraper_graph import ejecutar_scraping_web
from playwright.sync_api import sync_playwright

STATIC_PLAN_PATH = os.path.join(os.path.dirname(__file__), "static_scraping_plans.json")

def cargar_plan_estatico(url):
    try:
        dominio = urlparse(url).netloc.replace("www.", "")
        with open(STATIC_PLAN_PATH, "r", encoding="utf-8") as f:
            planes = json.load(f)
        if dominio in planes:
            print(f"[SCRAPER] Planificación estática encontrada para: {dominio}")
            return planes[dominio]
    except Exception as e:
        print(f"[SCRAPER] Error al cargar planificación estática: {e}")
    return None

def obtener_html_cloudscraper(url):
    print("[SCRAPER] Intentando obtener HTML con Cloudscraper...")
    try:
        scraper = cloudscraper.create_scraper()
        response = scraper.get(url)
        if response.status_code == 200:
            print("[SCRAPER] Cloudscraper obtuvo respuesta 200")
            return response.text
        else:
            print(f"[SCRAPER] Cloudscraper fallo con código {response.status_code}")
            return None
    except Exception as e:
        print(f"[SCRAPER] Error con Cloudscraper: {e}")
        return None

def obtener_html_tor(url):
    print("[SCRAPER] Intentando obtener HTML vía Tor...")
    proxies = {
        'http': 'socks5h://127.0.0.1:9050',
        'https': 'socks5h://127.0.0.1:9050'
    }
    try:
        response = requests.get(url, proxies=proxies, timeout=15)
        if response.status_code == 200:
            print("[SCRAPER] HTML recibido correctamente por Tor")
            return response.text
        else:
            print(f"[SCRAPER] Tor devolvió código: {response.status_code}")
            return None
    except Exception as e:
        print(f"[SCRAPER] Error usando Tor: {e}")
        return None

def obtener_selectores_y_plan_con_html(url: str, html: str) -> dict:
    prompt_system = (
        "Eres un extractor experto de selectores de scraping web en formato CSS. "
        "Devuelve únicamente un JSON válido, sin comentarios, sin explicaciones. "
        "Estructura exacta: { 'selectores': {...}, 'scroll': true/false, 'click_mas': '...', 'apartados': [...] }. "
        "No pongas 'scroll', 'click_mas' ni 'apartados' dentro de 'selectores'."
    )
    prompt_user = f"""
    Analiza esta página {url} y responde solo con el JSON siguiente:
    {{
    "selectores": {{"nombre": "...", "precio": "...", "disponibilidad": "..."}},
  "scroll": true/false,
  "     click_mas": "...",
  " apartados": ["...", "..."]
}}  
        Devuélvelo sin explicaciones, solo el JSON.
    HTML:
{html[:6000]}
"""
    try:
        r = requests.post(
            "http://localhost:11434/api/chat",
            json={
                "model": "mistral",
                "stream": False,
                "messages": [
                    {"role": "system", "content": prompt_system},
                    {"role": "user", "content": prompt_user}
                ]
            }
        )
        data = r.json()
        content = data["message"]["content"]
        print("[DEBUG] Respuesta cruda de la IA:", content)

        try:
            plan = json.loads(content)
            if not all(k in plan for k in ["selectores", "scroll", "click_mas", "apartados"]):
                raise ValueError("Plan incompleto o mal estructurado")
            return plan
        except Exception as je:
            print(f"[ERROR] La IA devolvió un JSON inválido o incompleto: {je}")
            with open("error_respuesta_ia.txt", "w", encoding="utf-8") as f:
                f.write(content)
            return {}

    except Exception as e:
        print(f"[ERROR] Fallo al obtener planificación de la IA: {e}")
        return {}

def extraer_con_playwright(plan):
    productos = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=100)
        page = browser.new_page()

        for pagina in plan.get("urls", []):
            print(f"[PLAYWRIGHT] Visitando {pagina}")
            page.goto(pagina, timeout=60000)
            print(f"[PLAYWRIGHT] URL actual: {page.url}")
            print("[PLAYWRIGHT] Esperando a que la página cargue completamente...")
            for _ in range(3):
                page.mouse.wheel(0, 5000)
                time.sleep(1.5)
            print("[PLAYWRIGHT] Espera adicional para que cargue todo el contenido dinámico...")
            time.sleep(5)
            try:
                boton_cookies = page.query_selector("button#onetrust-accept-btn-handler")
                if boton_cookies:
                     print("[PLAYWRIGHT] Aceptando cookies...")
                     boton_cookies.click()
                     time.sleep(2)
            except Exception as e:
                        print(f"[PLAYWRIGHT] No se pudo aceptar cookies: {e}")
            try:
                page.wait_for_load_state("domcontentloaded", timeout=15000)
            except:
                print("[PLAYWRIGHT] Timeout esperando DOMContentLoaded, continuando...")
                time.sleep(3)

            if plan.get("scroll"):
                for _ in range(5):
                    page.mouse.wheel(0, 10000)
                    time.sleep(1.5)

            while True:
                items = page.query_selector_all(plan["apartados"][0])
                print(f"[PLAYWRIGHT] Contenedores detectados: {len(items)}")
                for item in items:
                    try:
                        nombre = item.query_selector(plan["selectores"]["nombre"]).inner_text().strip()
                    except:
                        nombre = "Desconocido"
                    try:
                        precio = item.query_selector(plan["selectores"]["precio"]).inner_text().strip()
                    except:
                        precio = "No disponible"
                    try:
                        disponibilidad = item.query_selector(plan["selectores"]["disponibilidad"]).inner_text().strip()
                    except:
                        disponibilidad = "Desconocida"

                    productos.append({
                        "nombre": nombre,
                        "precio": precio,
                        "disponibilidad": disponibilidad
                    })

                # Manejo de click_mas: selector definido o autodetectar
                click_selector = plan.get("click_mas")
                next_button = None

                if click_selector:
                    try:
                        next_button = page.query_selector(click_selector)
                    except:
                        pass
                else:
                    # Detección automática: buscar botones comunes
                    for texto in ["Cargar más", "Ver más", "Mostrar más", "Siguiente"]:
                        try:
                            next_button = page.query_selector(f'button:has-text("{texto}")')
                            if next_button:
                                print(f"[PLAYWRIGHT] Botón detectado automáticamente por texto: {texto}")
                                break
                        except:
                            continue
                if next_button:
                    old_url = page.url
                    old_url = page.url
                    print("[PLAYWRIGHT] Clic en botón siguiente...")
                    try:
                        next_button.click()
                        for _ in range(10):  # espera activa max 5 segundos
                            time.sleep(0.5)
                            new_url = page.url
                            if new_url != old_url:
                                break
                        else:
                            print("[PLAYWRIGHT] La URL no ha cambiado tras esperar. Finalizando bucle.")
                            break
                        print(f"[PLAYWRIGHT] Nueva URL tras clic: {new_url}")
                    except Exception as e:
                        print(f"[PLAYWRIGHT] Error al hacer clic en el botón: {e}")
                        break
        browser.close()
    return productos

def ejecutar_scraping(url: str, instrucciones: str):
    dominio = urlparse(url).netloc.replace("www.", "")
    plan = cargar_plan_estatico(url)

    if dominio == "carrefour.es":
        if not plan:
            return {"error": "No hay plan estático para Carrefour"}
        print("[SCRAPER] Usando Playwright para Carrefour")
        productos = extraer_con_playwright(plan)
        return {"productos": productos, "fuente": "playwright"}

    print("[SCRAPER] Iniciando FlareSolverr...")
    flaresolverr_proc = start_flaresolverr()
    print("[SCRAPER] FlareSolverr iniciado.")

    options = uc.ChromeOptions()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--start-maximized")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    options.headless = False

    driver = uc.Chrome(options=options)

    try:
        stealth(driver,
                languages=["es-ES", "es"],
                vendor="Google Inc.",
                platform="Win32",
                webgl_vendor="Intel Inc.",
                renderer="Intel Iris OpenGL Engine",
                fix_hairline=True)

        print("[SCRAPER] Abriendo página en navegador UC...")
        driver.get(url)
        time.sleep(50)

        html = driver.page_source
        print("[DEBUG] HTML enviado a la IA (recortado):\n", html[:2000])

        if "challenge" in html or "verificación" in html.lower():
            print("[ERROR] Bloqueo detectado en Selenium. Intentando Cloudscraper...")
            html = obtener_html_cloudscraper(url)
            if html:
                plan = plan or obtener_selectores_y_plan_con_html(url, html)
                if plan:
                    return ejecutar_scraping_web(url, instrucciones)
                else:
                    return {"error": "Cloudscraper no generó plan"}

            print("[ERROR] Cloudscraper falló. Probando Tor...")
            html = obtener_html_tor(url)
            if html:
                plan = plan or obtener_selectores_y_plan_con_html(url, html)
                if plan:
                    return ejecutar_scraping_web(url, instrucciones)
                else:
                    return {"error": "Tor no generó plan"}

            print("[ERROR] Todos los métodos fallaron. Usando scraper alternativo.")
            return ejecutar_scraping_web(url, instrucciones)

        plan = plan or obtener_selectores_y_plan_con_html(url, html)
        if not plan or "selectores" not in plan:
            return {"error": "No se pudo obtener planificación de la IA"}

        print("[DEBUG] Plan de scraping:", json.dumps(plan, indent=2))
        productos = []
        urls = plan.get("urls") or [url]
        for pagina in urls:
            print(f"[SCRAPER] Visitando página del plan: {pagina}")
            driver.get(pagina)
            time.sleep(3)
            productos.extend(extraer_productos_en_pagina(driver, plan))

        print(f"[LOG] Total de productos recopilados: {len(productos)}")
        return {"productos": productos, "fuente": "selenium_uc"}

    except Exception as e:
        print(f"[ERROR] Fallo en scraping: {str(e)}")
        return {"error": str(e)}

    finally:
        driver.quit()
        if flaresolverr_proc:
            flaresolverr_proc.terminate()
            print("[SCRAPER] FlareSolverr detenido.")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(json.dumps({"error": "URL e instrucciones requeridas"}))
    else:
        url = sys.argv[1]
        instrucciones = sys.argv[2]
        resultado = ejecutar_scraping(url, instrucciones)
        print(json.dumps(resultado, indent=2))
def ejecutar_scraping_una_pagina(url: str, instrucciones: str):
    from urllib.parse import urlparse
    from playwright.sync_api import sync_playwright

    plan = cargar_plan_estatico(url)
    if not plan or "selectores" not in plan or "apartados" not in plan:
        return {"error": "No hay plan válido para esta URL"}

    productos = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=100)
        page = browser.new_page()
        print(f"[SCRAPER] Abriendo página: {url}")
        page.goto(url, timeout=60000)

        try:
            page.wait_for_load_state("domcontentloaded", timeout=10000)
            print("[SCRAPER] DOM cargado.")
        except:
            print("[SCRAPER] Timeout esperando DOMContentLoaded.")

        # Aceptar cookies
        try:
            btn = page.query_selector("button#onetrust-accept-btn-handler")
            if btn:
                print("[SCRAPER] Aceptando cookies.")
                btn.click()
                time.sleep(1.5)
        except:
            print("[SCRAPER] No se detectó botón de cookies.")

        # Scroll adicional
        print("[SCRAPER] Haciendo scroll para cargar contenido dinámico.")
        if plan.get("scroll", False):
            print("[SCRAPER] Bajando lentamente...")
            for _ in range(5):
                page.mouse.wheel(0, 1000)
                time.sleep(1.0)
            time.sleep(1.5)
        print("[SCRAPER] Subiendo lentamente...")
        for _ in range(5):
            page.mouse.wheel(0, -1000)
            time.sleep(1.0)
        print("[SCRAPER] Scroll completo.")
        
        # Tiempo extra de seguridad
        print("[SCRAPER] Esperando tiempo adicional por seguridad...")
        time.sleep(3)

        # Extraer productos
        items = page.query_selector_all(plan["apartados"][0])
        print(f"[SCRAPER] Contenedores encontrados: {len(items)}")

        for item in items:
            try:
                nombre = item.query_selector(plan["selectores"]["nombre"]).inner_text().strip()
            except:
                nombre = "Desconocido"
            try:
                precio = item.query_selector(plan["selectores"]["precio"]).inner_text().strip()
            except:
                precio = "No disponible"
            try:
                disponibilidad = item.query_selector(plan["selectores"]["disponibilidad"]).inner_text().strip()
            except:
                disponibilidad = "Desconocida"

            productos.append({
                "nombre": nombre,
                "precio": precio,
                "disponibilidad": disponibilidad
            })

        browser.close()
    return {"productos": productos, "fuente": "playwright", "url": url}
