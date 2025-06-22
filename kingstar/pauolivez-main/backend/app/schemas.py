from fastapi_users import schemas

class UserRead(schemas.BaseUser[int]):
    role: str

class UserCreate(schemas.BaseUserCreate):
    role: str

class UserUpdate(schemas.BaseUserUpdate):
    role: str