from logging.config import fileConfig

from alembic import context

from app.database import get_engine


config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)


def run_migrations_online() -> None:
    engine = get_engine()

    try:
        with engine.connect() as connection:
            context.configure(
                connection=connection,
                target_metadata=None,
                version_table_schema="public",
            )

            with context.begin_transaction():
                context.run_migrations()
    finally:
        engine.dispose()


if context.is_offline_mode():
    raise RuntimeError(
        "Offline migrations are not configured yet. "
        "Use the configured development database."
    )
else:
    run_migrations_online()