import subprocess
import json

def ejecutar_scrape_externo(url: str, instrucciones: str) -> dict:
    result = subprocess.run(
        ["venv\\Scripts\\python.exe", "app/scrape_script.py", url, instrucciones],
        capture_output=True,
        text=True
    )

    stdout = result.stdout.strip()

    # Busca el primer carácter válido JSON
    json_start = stdout.find("{")
    if json_start == -1:
        return {"error": "No se encontró contenido JSON válido.", "raw_stdout": stdout}

    try:
        cleaned = stdout[json_start:]
        return json.loads(cleaned)
    except json.JSONDecodeError as e:
        return {
            "error": f"Error al parsear JSON: {str(e)}",
            "raw_stdout": cleaned
        }