from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context

# Carga configuración de Alembic
config = context.config

# Configuración de logging (opcional)
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# 👇 IMPORTANTE: importa tus modelos y Base de SQLAlchemy
from app.database import Base
from app import models  # importa tus modelos para detectar las tablas

# 👇 Esto le dice a Alembic qué metadatos usar para detectar cambios
target_metadata = Base.metadata

# Offline migrations
def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()

# Online migrations
def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()

# Ejecutar según modo
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
