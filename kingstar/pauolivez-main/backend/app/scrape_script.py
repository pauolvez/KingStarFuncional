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
from patchright.sync_api import sync_playwright

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
        browser = p.chromium.launch(
            headless=False,
            slow_mo=150,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-infobars",
                "--disable-extensions",
                "--disable-web-security",
                "--start-maximized",
                "--disable-blink-features",
                "--disable-features=IsolateOrigins,site-per-process"
            ]
        )

        page = context.new_page()
        page.add_init_script("""
            // Oculta WebDriver
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });

            // Plugins falsos
            Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });

            // Idioma como navegador real
            Object.defineProperty(navigator, 'languages', { get: () => ['es-ES', 'es'] });

            // Plataforma y fabricante como Windows real
            Object.defineProperty(navigator, 'platform', { get: () => 'Win32' });
            Object.defineProperty(navigator, 'vendor', { get: () => 'Google Inc.' });

            // Chrome runtime simulado
            window.chrome = { runtime: {} };

            // Fingerprint WebGL simulado
            const getParameter = WebGLRenderingContext.prototype.getParameter;
            WebGLRenderingContext.prototype.getParameter = function(parameter) {
                if (parameter === 37445) return 'Intel Inc.';
                if (parameter === 37446) return 'Intel Iris OpenGL Engine';
                return getParameter.call(this, parameter);
            };

            // AudioContext fingerprint (opcional)
            const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
            const oscillator = audioCtx.createOscillator();
            oscillator.frequency.value = 440;
            oscillator.start(0);
        """)
        context = browser.new_context(
            storage_state=storage_path,
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            locale="es-ES",
            viewport={"width": 1280, "height": 800},
            extra_http_headers={
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
                "Accept-Encoding": "gzip, deflate, br",
                "Accept-Language": "es-ES,es;q=0.9",
                "Cache-Control": "max-age=0",
                "Connection": "keep-alive",
                "Referer": "https://www.fnac.es/",
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "same-origin",
                "Sec-Fetch-User": "?1",
                "Upgrade-Insecure-Requests": "1"
            }
        )
        page = context.new_page()
        page.add_init_script("""
            // Oculta WebDriver
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });

            // Plugins falsos
            Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });

            // Idioma como navegador real
            Object.defineProperty(navigator, 'languages', { get: () => ['es-ES', 'es'] });

            // Plataforma y fabricante como Windows real
            Object.defineProperty(navigator, 'platform', { get: () => 'Win32' });
            Object.defineProperty(navigator, 'vendor', { get: () => 'Google Inc.' });

            // Chrome runtime simulado
            window.chrome = { runtime: {} };

            // Fingerprint WebGL simulado
            const getParameter = WebGLRenderingContext.prototype.getParameter;
            WebGLRenderingContext.prototype.getParameter = function(parameter) {
                if (parameter === 37445) return 'Intel Inc.';
                if (parameter === 37446) return 'Intel Iris OpenGL Engine';
                return getParameter.call(this, parameter);
            };

            // AudioContext fingerprint (opcional)
            const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
            const oscillator = audioCtx.createOscillator();
            oscillator.frequency.value = 440;
            oscillator.start(0);
        """)
        page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3]});
            Object.defineProperty(navigator, 'languages', {get: () => ['es-ES', 'es']});
        """)


        for pagina in plan.get("urls", []):
            print(f"[PLAYWRIGHT] Visitando {pagina}")
            page.goto(pagina, timeout=60000)
            print(f"[PLAYWRIGHT] URL actual: {page.url}")
            print("[PLAYWRIGHT] Esperando a que la página cargue completamente...")

            # Verificación de presencia de precio tras máximo 20 segundos
            precio_selectores = plan["selectores"].get("precio")
            print(f"[VERIFICACIÓN] Buscando selector de precio(s): {precio_selectores}")
            precio_visible = False
            for i in range(20):  # Esperar hasta 20s en intervalos de 1s

                if isinstance(precio_selectores, list):
                    for sel in precio_selectores:
                        if page.query_selector(sel):
                            precio_visible = True
                            print(f"[✅] Selector de precio detectado: {sel} (tras {i+1} intentos)")
                            break
                else:
                    if page.query_selector(precio_selectores):
                        precio_visible = True
                if precio_visible:
                    print(f"[VERIFICACIÓN] Precio detectado tras {i+1} segundos.")
                    break
                time.sleep(1)

            if not precio_visible:
                print("[❌] No se detectó ningún precio tras 20 segundos. Saltando página.")
                continue  # Pasar al siguiente enlace del plan
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
                    precio = "No disponible"
                    precios_selectores = plan["selectores"].get("precio")
                    if isinstance(precios_selectores, list):
                        for sel in precios_selectores:
                            try:
                                if "fnac.es" in dominio:
                                    precio_raw = item.query_selector(sel) or page.query_selector(sel)
                                else:
                                    precio_raw = item.query_selector(sel)
                                if precio_raw:
                                    precio = precio_raw.inner_text().strip()
                                    break
                            except:
                                continue
                    else:
                        try:
                            from urllib.parse import urlparse
                            import re

                            # Justo antes de recorrer los productos
                            dominio = urlparse(url).netloc

                            # Dentro del bucle for item in items:
                            precio = "No disponible"
                            precios_selectores = plan["selectores"].get("precio")
                            if isinstance(precios_selectores, list):
                                for sel in precios_selectores:
                                    try:
                                        if "fnac.es" in dominio:
                                            precio_raw = item.query_selector(sel) or page.query_selector(sel)
                                        else:
                                            precio_raw = item.query_selector(sel)
                                        if precio_raw:
                                            texto_precio = precio_raw.inner_text().strip()

                                            # ✅ Solo limpiar si es FNAC
                                            if "fnac.es" in dominio:
                                                coincidencias = re.findall(r"\d{1,3}(?:[\.,]\d{2})?\s?€", texto_precio)
                                                precio = coincidencias[0] if coincidencias else texto_precio
                                            else:
                                                precio = texto_precio
                                            break
                                    except:
                                        continue
                            else:
                                try:
                                    precio_raw = item.query_selector(precios_selectores)
                                    if precio_raw:
                                        texto_precio = precio_raw.inner_text().strip()

                                        if "fnac.es" in dominio:
                                            coincidencias = re.findall(r"\d{1,3}(?:[\.,]\d{2})?\s?€", texto_precio)
                                            precio = coincidencias[0] if coincidencias else texto_precio
                                        else:
                                            precio = texto_precio
                                except:
                                    precio = "No disponible"

                        except:
                            precio = "No disponible"
                    try:
                        imagen = item.query_selector(plan["selectores"].get("imagen", "img")).get_attribute("src")
                        if imagen and imagen.startswith("//"):
                            imagen = "https:" + imagen
                    except:
                        imagen = "No disponible"
                    try:
                        url_producto = item.query_selector(plan["selectores"].get("url")).get_attribute("href")
                        if url_producto and not url_producto.startswith("http"):
                            from urllib.parse import urlparse
                            dominio = urlparse(url).netloc
                            url_producto = f"https://{dominio}{url_producto}"
                    except:
                        url_producto = "No disponible"

                    productos.append({
                        "nombre": nombre,
                        "precio": precio,
                        "imagen": imagen,
                        "url": url_producto
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
        context.storage_state(path=storage_path)
        browser.close()
    return productos

def ejecutar_scraping(url: str, instrucciones: str):
    dominio = urlparse(url).netloc.replace("www.", "")
    plan = cargar_plan_estatico(url)

    if dominio == "carrefour.es":
        if not plan:
            return {"error": "No hay plan estático para Carrefour"}
        print("[SCRAPER] Usando Playwright para Carrefour")
        resultado = ejecutar_scraping_una_pagina(url, instrucciones)
        return resultado

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
    from patchright.sync_api import sync_playwright

    plan = cargar_plan_estatico(url)
    if not plan or "selectores" not in plan or "apartados" not in plan:
        return {"error": "No hay plan válido para esta URL"}

    productos = []
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,
            slow_mo=150,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-infobars",
                "--disable-extensions",
                "--disable-web-security",
                "--start-maximized",
                "--disable-blink-features",
                "--disable-features=IsolateOrigins,site-per-process"
            ]
        )

        import os
        storage_path = os.path.join(os.path.dirname(__file__), "storage", "fnac.json")
        if not os.path.exists(storage_path):
            with open(storage_path, "w", encoding="utf-8") as f:
                f.write("{}")

        context = browser.new_context(
            storage_state=storage_path,
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            locale="es-ES",
            viewport={"width": 1280, "height": 800},
            extra_http_headers={
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
                "Accept-Encoding": "gzip, deflate, br",
                "Accept-Language": "es-ES,es;q=0.9",
                "Cache-Control": "max-age=0",
                "Connection": "keep-alive",
                "Referer": "https://www.fnac.es/",
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "same-origin",
                "Sec-Fetch-User": "?1",
                "Upgrade-Insecure-Requests": "1"
            }
        )


        page = context.new_page()
        page.add_init_script("""
            // Oculta WebDriver
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });

            // Plugins falsos
            Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });

            // Idioma como navegador real
            Object.defineProperty(navigator, 'languages', { get: () => ['es-ES', 'es'] });

            // Plataforma y fabricante como Windows real
            Object.defineProperty(navigator, 'platform', { get: () => 'Win32' });
            Object.defineProperty(navigator, 'vendor', { get: () => 'Google Inc.' });

            // Chrome runtime simulado
            window.chrome = { runtime: {} };

            // Fingerprint WebGL simulado
            const getParameter = WebGLRenderingContext.prototype.getParameter;
            WebGLRenderingContext.prototype.getParameter = function(parameter) {
                if (parameter === 37445) return 'Intel Inc.';
                if (parameter === 37446) return 'Intel Iris OpenGL Engine';
                return getParameter.call(this, parameter);
            };

            // AudioContext fingerprint (opcional)
            const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
            const oscillator = audioCtx.createOscillator();
            oscillator.frequency.value = 440;
            oscillator.start(0);
        """)
        page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3]});
            Object.defineProperty(navigator, 'languages', {get: () => ['es-ES', 'es']});
        """)
        print(f"[SCRAPER] Abriendo página: {url}")
        page.goto(url, timeout=60000)
        page.wait_for_load_state("networkidle")
        time.sleep(2.5)

        # Simulación de scroll irregular
        for i in range(6):
            scroll_y = 200 + (i * 100)
            page.mouse.wheel(0, scroll_y)
            print(f"[SIMULACIÓN] Scroll hacia abajo {scroll_y}px")
            time.sleep(1.2)

        # Simular pequeños movimientos del ratón
        for _ in range(5):
            x = 200 + (_ * 20)
            y = 300 + (_ * 15)
            page.mouse.move(x, y)
            print(f"[SIMULACIÓN] Movimiento del ratón a ({x}, {y})")
            time.sleep(0.5)

        # Clic en zona segura (no enlaces)
        try:
            print("[SIMULACIÓN] Clic en zona aleatoria segura")
            page.mouse.click(50, 150)
            time.sleep(0.8)
        except:
            pass

        # Simular pulsación de tecla hacia abajo
        try:
            page.keyboard.press("ArrowDown")
            page.keyboard.press("ArrowDown")
            page.keyboard.press("ArrowUp")
            print("[SIMULACIÓN] Pulsaciones de flechas simuladas")
            time.sleep(1)
        except:
            pass

        # Simulación de navegación humana antes del scraping
        page.wait_for_load_state("networkidle")
        time.sleep(3)

        # Scroll inicial
        for _ in range(3):
            page.mouse.wheel(0, 300)
            time.sleep(1)

        # Clic simulado en enlace, luego volver atrás
        try:
            enlace = page.query_selector("a[href*='/a']")
            if enlace:
                print("[SIMULACIÓN] Clic en un enlace aleatorio antes del scraping...")
                enlace.click()
                time.sleep(3)
                page.go_back()
                time.sleep(1.5)
        except:
            print("[SIMULACIÓN] No se encontró enlace para simular clic.")

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
        precio_selectores = plan["selectores"].get("precio")
        precio_visible = False

        for i in range(20):  # Hasta 20 segundos
            if isinstance(precio_selectores, list):
                for sel in precio_selectores:
                    if page.query_selector(sel):
                        precio_visible = True
                        print(f"[✅] Selector de precio detectado: {sel} (tras {i+1} intentos)")
                        break
            else:
                if page.query_selector(precio_selectores):
                    precio_visible = True
                    print(f"[✅] Selector de precio detectado: {precio_selectores} (tras {i+1} intentos)")

            if precio_visible:
                print(f"[VERIFICACIÓN] Precio detectado tras {i+1} segundos.")

                break
            time.sleep(1)

        if not precio_visible:
            print("[❌] No se detectó ningún precio tras 20 segundos. Cancelando scraping.")
            browser.close()
            return {"productos": [], "fuente": "playwright", "url": url}

        # Scroll adicional
        print("[SCRAPER] Haciendo scroll para cargar contenido dinámico.")
        if plan.get("scroll", False):
            print("[SCRAPER] Bajando lentamente...")
            for i in range(10):
                page.mouse.wheel(0, 500)  # Scroll más suave
                print(f"[SCROLL ↓] Paso {i+1}")
                time.sleep(1.2)
            time.sleep(2)
        print("[SCRAPER] Scroll completo.")

            #print("[SCRAPER] Subiendo lentamente...")
            #for i in range(10):
                #page.mouse.wheel(0, -500)
                #print(f"[SCROLL ↑] Paso {i+1}")
                #time.sleep(1.2)
            #time.sleep(2)
        
        # Tiempo extra de seguridad
        print("[SCRAPER] Esperando tiempo adicional por seguridad...")
        time.sleep(1.5)

        # Verificación de presencia de precio antes de continuar
        precio_selectores = plan["selectores"].get("precio")
        print(f"[VERIFICACIÓN] Buscando selector de precio(s): {precio_selectores}")
        precio_visible = False

        for i in range(20):  # Hasta 20 segundos
            if isinstance(precio_selectores, list):
                for sel in precio_selectores:
                    if page.query_selector(sel):
                        precio_visible = True
                        print(f"[✅] Selector de precio detectado: {sel} (tras {i+1} intentos)")
                        break
            else:
                if page.query_selector(precio_selectores):
                    precio_visible = True
                    print(f"[✅] Selector de precio detectado: {precio_selectores} (tras {i+1} intentos)")

            if precio_visible:
                print(f"[VERIFICACIÓN] Precio detectado tras {i+1} segundos.")
                break
            else:
                if page.query_selector(precio_selectores):
                    precio_visible = True
                    print(f"[✅] Selector de precio detectado: {precio_selectores} (tras {i+1} intentos)")
            if precio_visible:
                print(f"[VERIFICACIÓN] Precio detectado tras {i+1} segundos.")
                break
            time.sleep(1)

        if not precio_visible:
            print("[❌] No se detectó ningún precio tras 20 segundos. Cancelando scraping.")
            context.storage_state(path=storage_path)
            browser.close()
            return {"productos": [], "fuente": "playwright", "url": url}

        # Extraer productos
        items = page.query_selector_all(plan["apartados"][0])
        print(f"[SCRAPER] Contenedores encontrados: {len(items)}")

        print(f"[SCRAPER] Contenedores encontrados: {len(items)}")

        from urllib.parse import urlparse

        for item in items:
            try:
                nombre = item.query_selector(plan["selectores"]["nombre"]).inner_text().strip()
            except:
                nombre = "Desconocido"

            precio = "No disponible"
            precios_selectores = plan["selectores"].get("precio")
            if isinstance(precios_selectores, list):
                for sel in precios_selectores:
                    try:
                        if "fnac.es" in dominio:
                            precio_raw = item.query_selector(sel) or page.query_selector(sel)
                        else:
                            precio_raw = item.query_selector(sel)
                        if precio_raw:
                            precio = precio_raw.inner_text().strip()
                            break
                    except:
                        continue
            else:
                try:
                    from urllib.parse import urlparse
                    import re

                    # Justo antes de recorrer los productos
                    dominio = urlparse(url).netloc

                    # Dentro del bucle for item in items:
                    precio = "No disponible"
                    precios_selectores = plan["selectores"].get("precio")
                    if isinstance(precios_selectores, list):
                        for sel in precios_selectores:
                            try:
                                if "fnac.es" in dominio:
                                    precio_raw = item.query_selector(sel) or page.query_selector(sel)
                                else:
                                    precio_raw = item.query_selector(sel)
                                if precio_raw:
                                    texto_precio = precio_raw.inner_text().strip()

                                    # ✅ Solo limpiar si es FNAC
                                    if "fnac.es" in dominio:
                                        coincidencias = re.findall(r"\d{1,3}(?:[\.,]\d{2})?\s?€", texto_precio)
                                        precio = coincidencias[0] if coincidencias else texto_precio
                                    else:
                                        precio = texto_precio
                                    break
                            except:
                                continue
                    else:
                        try:
                            precio_raw = item.query_selector(precios_selectores)
                            if precio_raw:
                                texto_precio = precio_raw.inner_text().strip()

                                if "fnac.es" in dominio:
                                    coincidencias = re.findall(r"\d{1,3}(?:[\.,]\d{2})?\s?€", texto_precio)
                                    precio = coincidencias[0] if coincidencias else texto_precio
                                else:
                                    precio = texto_precio
                        except:
                            precio = "No disponible"

                except:
                    precio = "No disponible"
            try:
                imagen = item.query_selector(plan["selectores"].get("imagen", "img")).get_attribute("src")
                if imagen and imagen.startswith("//"):
                    imagen = "https:" + imagen
            except:
                imagen = "No disponible"

            try:
                url_producto = item.query_selector(plan["selectores"].get("url")).get_attribute("href")
                if url_producto and not url_producto.startswith("http"):
                    dominio = urlparse(url).netloc
                    url_producto = f"https://{dominio}{url_producto}"
            except:
                url_producto = "No disponible"

            productos.append({
                "nombre": nombre,
                "precio": precio,
                "imagen": imagen,
                "url": url_producto
            })
            if len(productos) % 10 == 0:
                print("[AUTO-GUARDADO] Guardando sesión...")
                context.storage_state(path=storage_path)
    return {"productos": productos, "fuente": "playwright", "url": url}

