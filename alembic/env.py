from logging.config import fileConfig
from sqlalchemy import engine_from_config
from sqlalchemy import pool
from alembic import context
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app.models import Base  # import Base ของ SQLAlchemy
from app.config import settings

print("DEBUG: Tables in metadata:", Base.metadata.tables.keys())

config = context.config
target_metadata = Base.metadata
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)
