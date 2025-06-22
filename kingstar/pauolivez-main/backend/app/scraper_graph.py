from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException
import time

def ejecutar_scraping_web(url: str, instrucciones: str):
    options = Options()
    options.add_argument("--headless=new")  # headless modo nuevo más fiable
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    driver = webdriver.Chrome(options=options)

    try:
        driver.get(url)
        time.sleep(2)

        # Intentar aceptar cookies si hay botón visible con múltiples selectores comunes
        try:
            print("[LOG] Buscando botón de cookies...")
            posibles_selectores = [
                "#cookies-accept-all",  # PCComponentes
                "button[mode='primary']",
                ".cookies__button",
                ".accept-cookies",
                "button.btn-accept",
                "button[aria-label*='Aceptar']"
            ]
            for selector in posibles_selectores:
                elementos = driver.find_elements(By.CSS_SELECTOR, selector)
                if elementos:
                    print(f"[LOG] Botón de cookies encontrado con selector: {selector}. Haciendo clic...")
                    driver.execute_script("arguments[0].click();", elementos[0])
                    time.sleep(2)
                    break
            else:
                print("[LOG] No se detectó botón de cookies visible.")
        except Exception as e:
            print(f"[WARN] Error durante la aceptación de cookies: {e}")

        todos_productos = []
        pagina = 1
        secciones_visitadas = set()

        print(f"[LOG] Iniciando scraping IA en: {url}")

        while True:
            print(f"[LOG] Página {pagina}: {driver.current_url}")
            soup = BeautifulSoup(driver.page_source, 'html.parser')

            contenedores = soup.select('.c-product-card__content')
            print(f"[LOG] Posibles contenedores detectados: {len(contenedores)}")

            for producto in contenedores:
                titulo = producto.select_one('.c-product-card__title')
                precio = producto.select_one('.c-product-card__price')
                disponibilidad = producto.select_one('.c-product-card__availability')

                if not titulo:
                    continue

                todos_productos.append({
                    "nombre": titulo.text.strip(),
                    "precio": precio.text.strip() if precio else "No disponible",
                    "disponibilidad": disponibilidad.text.strip() if disponibilidad else "Desconocida"
                })

            print(f"[LOG] Productos encontrados en esta página: {len(todos_productos)}")

            # Buscar botón "Cargar más"
            try:
                cargar_mas = WebDriverWait(driver, 3).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "button.load-more, .load-more-btn"))
                )
                print("[LOG] Pulsando botón de 'Cargar más'")
                driver.execute_script("arguments[0].click();", cargar_mas)
                time.sleep(3)
                continue
            except:
                pass

            # Buscar botón "Siguiente página"
            next_btn = soup.select_one('li.next > a, a[rel="next"], .pagination-next a')
            if next_btn:
                href = next_btn.get('href')
                if not href.startswith("http"):
                    base = "/".join(driver.current_url.split('/')[:3])
                    href = base + href if href.startswith('/') else f"{driver.current_url.rstrip('/')}/{href}"
                print(f"[LOG] Navegando a: {href}")
                driver.get(href)
                pagina += 1
                time.sleep(3)
            else:
                print("[LOG] Fin del paginado. Buscando otras secciones.")
                links = soup.select('a[href]')
                nuevos_links = [
                    l['href'] for l in links
                    if "portatiles" in l['href'] or "producto" in l['href']
                    and l['href'] not in secciones_visitadas
                    and not l['href'].startswith('#')
                ]

                if nuevos_links:
                    siguiente = nuevos_links[0]
                    secciones_visitadas.add(siguiente)
                    if not siguiente.startswith("http"):
                        base = "/".join(driver.current_url.split('/')[:3])
                        siguiente = base + siguiente if siguiente.startswith('/') else f"{driver.current_url.rstrip('/')}/{siguiente}"
                    print(f"[LOG] Explorando nueva sección: {siguiente}")
                    driver.get(siguiente)
                    time.sleep(3)
                    pagina = 1
                    continue
                else:
                    print("[LOG] No se encontraron más secciones navegables.")
                    break

        print(f"[LOG] Total de productos recopilados: {len(todos_productos)}")
        return {"productos": todos_productos}

    except Exception as e:
        print(f"[ERROR] Fallo en scraping: {str(e)}")
        return {"error": str(e)}

    finally:
        driver.quit()
