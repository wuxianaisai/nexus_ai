import requests
import psycopg2
from backend.app.config import DB_CONFIG, DATA_DRAGON_VERSION

# Подключение к БД
try:
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()
except psycopg2.Error as e:
    raise Exception(f"Ошибка подключения к БД: {e}")

def load_champions(version=DATA_DRAGON_VERSION):
    try:
        url = f"http://ddragon.leagueoflegends.com/cdn/{version}/data/en_US/champion.json"
        response = requests.get(url)
        if response.status_code != 200:
            print(f"Ошибка загрузки Data Dragon: HTTP {response.status_code}, {response.text}")
            return

        data = response.json()["data"]
        for champ_name, champ_data in data.items():
            champion_id = int(champ_data["key"])
            name = champ_data["name"]
            tags = champ_data["tags"]
            difficulty = champ_data["info"]["difficulty"]
            primary_role = champ_data["tags"][0] if champ_data["tags"] else None

            cursor.execute("""
                INSERT INTO champions (champion_id, name, version, tags, difficulty, primary_role)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT ON CONSTRAINT unique_champion DO UPDATE
                SET name = EXCLUDED.name,
                    tags = EXCLUDED.tags,
                    difficulty = EXCLUDED.difficulty,
                    primary_role = EXCLUDED.primary_role
            """, (champion_id, name, version, tags, difficulty, primary_role))

        conn.commit()
        print(f"Таблица champions заполнена для версии {version}")
    except Exception as e:
        conn.rollback()
        print(f"Ошибка при загрузке чемпионов: {e}")
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    version = input("Введите версию патча (e.g., 15.19.1, default: {}): ".format(DATA_DRAGON_VERSION)) or DATA_DRAGON_VERSION
    load_champions(version)