from fastapi_users_db_sqlalchemy import SQLAlchemyBaseUserTable
from sqlalchemy import Integer, String, Float, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base
import uuid
from datetime import datetime


class User(SQLAlchemyBaseUserTable[int], Base):
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    role: Mapped[str] = mapped_column(String(length=20), default="vendedor")
    plan: Mapped[str] = mapped_column(String(length=20), default="gratis")  # gratis o premium


class ProductoScrapeado(Base):
    __tablename__ = "productos_scrapeados"
    __table_args__ = (UniqueConstraint("url_proveedor", name="uq_producto_url"),)

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    nombre: Mapped[str] = mapped_column(String)
    imagen_url: Mapped[str] = mapped_column(String)
    url_proveedor: Mapped[str] = mapped_column(String)
    precio_proveedor: Mapped[float] = mapped_column(Float)
    proveedor: Mapped[str] = mapped_column(String)
    fecha_scraping: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    estado: Mapped[str] = mapped_column(String, default="pendiente")


class ProductoComparado(Base):
    __tablename__ = "productos_comparados"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    id_scrapeado: Mapped[str] = mapped_column(ForeignKey("productos_scrapeados.id"))
    url_amazon: Mapped[str] = mapped_column(String)
    asin: Mapped[str] = mapped_column(String)
    precio_amazon: Mapped[float] = mapped_column(Float)
    rentabilidad_fba: Mapped[float] = mapped_column(Float)
    rentabilidad_drops: Mapped[float] = mapped_column(Float)
    estimacion_ventas: Mapped[int] = mapped_column(Integer)
    fecha_comparacion: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ProductoAprobado(Base):
    __tablename__ = "productos_aprobados"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    id_comparado: Mapped[str] = mapped_column(ForeignKey("productos_comparados.id"))
    metodo_venta: Mapped[str] = mapped_column(String)  # FBA o Dropshipping
    precio_tienda: Mapped[float] = mapped_column(Float)
    stock: Mapped[int] = mapped_column(Integer, default=0)  # Dropshipping: stock infinito (lógico)
    estado: Mapped[str] = mapped_column(String, default="activo")  # activo, sin_stock, margen_bajo
    fecha_aprobacion: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class HistorialPrecios(Base):
    __tablename__ = "historial_precios"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    id_aprobado: Mapped[str] = mapped_column(ForeignKey("productos_aprobados.id"))
    precio_amazon: Mapped[float] = mapped_column(Float)
    margen_actual: Mapped[float] = mapped_column(Float)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
