import asyncio
import sys
import subprocess
from fastapi import FastAPI, Query
from app.auth import fastapi_users, auth_backend
from app.users import UserRead, UserCreate, UserUpdate
from app.models import User
from app.database import Base, engine
from app.ollama_client import query_ollama
from app.wrapper_scraper import ejecutar_scrape_externo
from concurrent.futures import ThreadPoolExecutor

# Fix para Windows
if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

app = FastAPI()
executor = ThreadPoolExecutor()

@app.on_event("startup")
async def on_startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

# Rutas de autenticación
app.include_router(
    fastapi_users.get_auth_router(auth_backend), prefix="/auth/jwt", tags=["auth"]
)
app.include_router(
    fastapi_users.get_register_router(UserRead, UserCreate), prefix="/auth", tags=["auth"]
)
app.include_router(
    fastapi_users.get_users_router(UserRead, UserUpdate), prefix="/users", tags=["users"]
)

@app.get("/")
def root():
    return {"mensaje": "Backend FastAPI funcionando correctamente con fastapi-users 14, IA y ScrapeGraphAI con Ollama"}

@app.get("/preguntar-ia")
async def preguntar_ia(pregunta: str = Query(..., min_length=3)):
    respuesta = await query_ollama(pregunta)
    return {"respuesta": respuesta}

@app.get("/scrap-web")
async def scrap_web(
    url: str = Query(..., min_length=10),
    instrucciones: str = Query(..., min_length=5)
):
    resultado = ejecutar_scrape_externo(url, instrucciones)
    return {"resultado": resultado}

@app.get("/scrap-externo")
async def scrap_externo(url: str = Query(...), instrucciones: str = Query(...)):
    result = subprocess.run(
        ["python", "app/wrapper_scraper.py", url, instrucciones],
        capture_output=True,
        text=True
    )
    return {"salida": result.stdout.strip()}
from app.scraper_controller import router as scraper_router
app.include_router(scraper_router, prefix="/scraper", tags=["scraping"])