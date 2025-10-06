import requests
import psycopg2
from datetime import datetime
import time
import json
from config import DB_CONFIG, API_KEY, HEADERS, REGION

# Подключение к БД
try:
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()
except psycopg2.Error as e:
    raise Exception(f"Ошибка подключения к БД: {e}")

def load_mastery(puuid):
    """Загружает данные мастерства чемпионов для игрока и вставляет в champion_mastery"""
    try:
        url = f"https://{REGION}.api.riotgames.com/lol/champion-mastery/v4/champion-masteries/by-puuid/{puuid}"
        response = requests.get(url, headers=HEADERS)
        time.sleep(1.2)  # Задержка для лимитов API
        if response.status_code != 200:
            print(f"Ошибка загрузки мастерства для puuid {puuid}: HTTP {response.status_code}, {response.text}")
            return False

        data = response.json()
        for mastery in data:
            champion_id = mastery["championId"]
            champion_level = mastery["championLevel"]
            champion_points = mastery["championPoints"]
            last_play_time = datetime.fromtimestamp(mastery["lastPlayTime"] / 1000) if mastery.get("lastPlayTime") else None
            tokens_earned = min(mastery.get("tokensEarned", 0), 20)  # Ограничиваем до 20
            champion_season_milestone = mastery.get("championSeasonMilestone", 0)
            milestone_grades = json.dumps(mastery.get("milestoneGrades", []))
            next_season_milestone = json.dumps(mastery.get("nextSeasonMilestone", {}))

            cursor.execute("""
                INSERT INTO champion_mastery (
                    puuid, champion_id, champion_level, champion_points, last_play_time, 
                    tokens_earned, champion_season_milestone, milestone_grades, next_season_milestone
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT ON CONSTRAINT champion_mastery_pkey DO UPDATE
                SET champion_level = EXCLUDED.champion_level,
                    champion_points = EXCLUDED.champion_points,
                    last_play_time = EXCLUDED.last_play_time,
                    tokens_earned = EXCLUDED.tokens_earned,
                    champion_season_milestone = EXCLUDED.champion_season_milestone,
                    milestone_grades = EXCLUDED.milestone_grades,
                    next_season_milestone = EXCLUDED.next_season_milestone
            """, (
                puuid, champion_id, champion_level, champion_points, last_play_time, 
                tokens_earned, champion_season_milestone, milestone_grades, next_season_milestone
            ))

        conn.commit()
        print(f"Мастерство чемпионов для puuid {puuid} сохранено")
        return True
    except psycopg2.Error as e:
        conn.rollback()
        print(f"Ошибка БД при загрузке мастерства для puuid {puuid}: {e}")
        return False
    except Exception as e:
        print(f"Ошибка при загрузке мастерства для puuid {puuid}: {e}")
        return False

def load_all_mastery():
    """Загружает мастерство для всех puuid из таблицы summoners"""
    try:
        cursor.execute("SELECT puuid FROM summoners")
        puuids = cursor.fetchall()
        total = len(puuids)
        print(f"Найдено {total} игроков для загрузки мастерства")

        for i, (puuid,) in enumerate(puuids, 1):
            print(f"Обработка {i}/{total}: puuid {puuid}")
            load_mastery(puuid)
            # Дополнительная задержка каждые 10 запросов для лимитов API (100/2мин)
            if i % 10 == 0:
                print("Пауза 10 секунд для соблюдения лимитов API...")
                time.sleep(10)

        print("Загрузка мастерства завершена")
    except psycopg2.Error as e:
        conn.rollback()
        print(f"Ошибка БД при загрузке всех puuid: {e}")
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    load_all_mastery()