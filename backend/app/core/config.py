import os
from dotenv import load_dotenv

load_dotenv()

# Which environment we're running in: "development" or "production"
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL is not set in .env file")

JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")