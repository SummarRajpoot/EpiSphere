import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    DATABASE_URL = os.getenv("DATABASE_URL")
    OPENWEATHERMAP_API_KEY = os.getenv("OPENWEATHERMAP_API_KEY")
    OPENAQ_API_URL = "https://api.openaq.org/v2"
    WEATHER_API_TIMEOUT = 10.0  # seconds

config = Config()
