from fastapi_users import schemas
from pydantic import BaseModel

# Modelos de usuario
class UserRead(schemas.BaseUser[int]):
    role: str

class UserCreate(schemas.BaseUserCreate):
    role: str

class UserUpdate(schemas.BaseUserUpdate):
    role: str

# Modelo para productos scrapings
class ProductoScrapeado(BaseModel):
    nombre: str
    precio: str
    url_producto: str
    url_imagen: str
