from alembic import context
from dotenv import load_dotenv

from backend.storage import database_url, engine, metadata

load_dotenv()


def run_migrations():
    if context.is_offline_mode():
        context.configure(url=database_url(), target_metadata=metadata, literal_binds=True)
        with context.begin_transaction():
            context.run_migrations()
    else:
        with engine(database_url()).connect() as connection:
            context.configure(connection=connection, target_metadata=metadata)
            with context.begin_transaction():
                context.run_migrations()


run_migrations()
