from dotenv import load_dotenv
import os

load_dotenv()

# Проверка, что все переменные окружения заданы
required_env_vars = ["DB_NAME", "DB_USER", "DB_PASSWORD", "DB_HOST", "RIOT_API_KEY"]
for var in required_env_vars:
    if not os.getenv(var):
        raise ValueError(f"Переменная окружения {var} не найдена в .env")

# Конфигурация базы данных
DB_CONFIG = {
    "dbname": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "host": os.getenv("DB_HOST")
}

# Конфигурация Riot API
API_KEY = os.getenv("RIOT_API_KEY")
HEADERS = {"X-Riot-Token": API_KEY}
REGION = "RU"
API_REGION = "europe"

# Роли для match_players
ROLES = {
    "TOP": 1,
    "JUNGLE": 2,
    "MIDDLE": 3,
    "BOTTOM": 4,
    "UTILITY": 5
}

# Версия Data Dragon
DATA_DRAGON_VERSION = "15.19.1"