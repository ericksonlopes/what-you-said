import importlib
import pkgutil
import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from alembic.autogenerate import rewriter
from alembic.operations import ops
from sqlalchemy import engine_from_config
from sqlalchemy import pool
from src.config.settings import settings
from src.infrastructure.repositories.sql.connector import Base

_package_name = "src.infrastructure.repositories.sql.models"

try:
    importlib.import_module(_package_name)
except ModuleNotFoundError:
    # env.py lives in <project_root>/alembic/env.py, so project root is two levels up
    project_root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(project_root))
    importlib.invalidate_caches()

try:
    _pkg = importlib.import_module(_package_name)
    if hasattr(_pkg, "__path__"):
        for _finder, _name, _ispkg in pkgutil.iter_modules(_pkg.__path__):
            if _name.startswith("_"):
                continue
            importlib.import_module(f"{_package_name}.{_name}")
except Exception:
    # Let the error surface during alembic operations so it's visible
    raise RuntimeError(f"The package could not be imported {_package_name}.")

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def include_object(obj, name, type_, reflected, compare_to):
    # Skip tables that exist only in the database (prevents autogenerate drop_table)
    if type_ == "table" and reflected and compare_to is None:
        return False
    return True


writer = rewriter.Rewriter()


@writer.rewrites(ops.CreateTableOp)
@writer.rewrites(ops.CreateIndexOp)
def add_if_not_exists(context, revision, op):
    op.if_not_exists = True
    return op


@writer.rewrites(ops.DropTableOp)
@writer.rewrites(ops.DropIndexOp)
def add_if_exists(context, revision, op):
    op.if_exists = True
    return op


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    context.configure(
        url=settings.sql.url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_object=include_object,
        process_revision_directives=writer,
        render_as_batch=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        url=settings.sql.url,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_object=include_object,
            process_revision_directives=writer,
            render_as_batch=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
