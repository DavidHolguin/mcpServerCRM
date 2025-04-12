from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from .config import settings

# Configuración de la base de datos
database_url = settings.DATABASE_URL

# Corrección para URLs que comienzan con 'https://'
if database_url.startswith('https://'):
    # Convertir de formato https:// a postgresql://
    database_url = database_url.replace('https://', 'postgresql://')

SQLALCHEMY_DATABASE_URL = database_url

engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()