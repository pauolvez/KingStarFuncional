import subprocess
import json

def ejecutar_scrape_externo(url: str, instrucciones: str) -> dict:
    try:
        result = subprocess.run(
            ["venv/Scripts/python", "app/scrape_script.py", url, instrucciones],
            capture_output=True,
            text=True
        )

        print("[WRAPPER] STDOUT:")
        print(result.stdout)
        print("[WRAPPER] STDERR:")
        print(result.stderr)

        # Intentar decodificar cualquier línea de salida que contenga JSON válido
        for line in reversed(result.stdout.strip().splitlines()):
            line = line.strip()
            if line.startswith("{") and line.endswith("}"):
                try:
                    parsed = json.loads(line)
                    # Si contiene error, reportarlo explícitamente
                    if "error" in parsed:
                        print("[WRAPPER] Error desde el script:", parsed["error"])
                    return parsed
                except json.JSONDecodeError:
                    continue

        # Si ninguna línea contiene JSON válido
        return {
            "error": "No se pudo obtener un JSON válido del script externo.",
            "raw_stdout": result.stdout,
            "raw_stderr": result.stderr
        }

    except Exception as e:
        return {"error": f"Excepción al ejecutar el subprocesso: {str(e)}"}
