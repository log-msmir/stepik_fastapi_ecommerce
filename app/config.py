import os
from dotenv import load_dotenv


load_dotenv()

SECRET_KEY = os.getenv('SECRET_KEY')
ALGORITHM = "HS256"
pg_name = os.getenv('POSTGRES_DB')
pg_user = os.getenv('POSTGRES_USER')
pg_password = os.getenv('POSTGRES_PASSWORD')
pg_port = os.getenv('POSTGRES_PORT')
DATABASE_URL = (
     'postgresql+asyncpg://'
     f'{pg_user}:{pg_password}@db:{pg_port}/{pg_name}'
)
