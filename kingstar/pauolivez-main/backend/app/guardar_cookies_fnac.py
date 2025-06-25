from playwright.sync_api import sync_playwright
import os
import time

storage_path = os.path.join(os.path.dirname(__file__), "storage", "fnac.json")

with sync_playwright() as p:
    browser = p.chromium.launch(
        headless=False,
        slow_mo=100,
        args=[
            "--disable-blink-features=AutomationControlled",
            "--disable-gpu",
            "--disable-software-rasterizer",
            "--no-sandbox",
            "--disable-dev-shm-usage",
            "--disable-infobars",
            "--disable-extensions",
            "--disable-web-security",
            "--start-maximized",
            "--disable-features=IsolateOrigins,site-per-process"
        ]
    )

    context = browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        locale="es-ES",
        viewport={"width": 1280, "height": 800},
        extra_http_headers={
            "Accept-Language": "es-ES,es;q=0.9"
        }
    )

    page = context.new_page()

    page.add_init_script("""
        Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
        Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3]});
        Object.defineProperty(navigator, 'languages', {get: () => ['es-ES', 'es']});
        Object.defineProperty(navigator, 'platform', {get: () => 'Win32'});
        Object.defineProperty(navigator, 'vendor', {get: () => 'Google Inc.'});
        window.chrome = { runtime: {} };
        const getParameter = WebGLRenderingContext.prototype.getParameter;
        WebGLRenderingContext.prototype.getParameter = function(parameter) {
            if (parameter === 37445) return 'Intel Inc.';
            if (parameter === 37446) return 'Intel Iris OpenGL Engine';
            return getParameter.call(this, parameter);
        };
    """)

    print("🌐 Abriendo FNAC...")
    page.goto("https://www.fnac.es", timeout=60000)

    print("🔓 Navega por la página como humano (acepta cookies, busca productos, etc.)")
    print("⏳ Cuando termines, vuelve a esta ventana y pulsa ENTER para guardar la sesión.")
    input("📝 Pulsa ENTER para guardar cookies y cerrar...")

    context.storage_state(path=storage_path)
    browser.close()
    print(f"✅ Cookies guardadas correctamente en: {storage_path}")
