import os
from dotenv import load_dotenv


load_dotenv()

SECRET_KEY = os.getenv('SECRET_KEY')
ALGORITHM = "HS256"
pg_name = os.getenv('PG_NAME')
pg_user = os.getenv('PG_USER')
pg_password = os.getenv('PG_PASSWORD')
pg_port = os.getenv('PG_PORT')
DATABASE_URL = (
     'postgresql+asyncpg://'
     f'{pg_user}:{pg_password}@localhost:{pg_port}/{pg_name}'
)
