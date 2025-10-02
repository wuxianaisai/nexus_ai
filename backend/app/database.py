import requests
import psycopg2
from datetime import datetime
import time
from dotenv import load_dotenv
import os

load_dotenv()

# Конфигурация
API_KEY = os.getenv("RIOT_API_KEY")
if not API_KEY:
    raise ValueError("RIOT_API_KEY не найден в .env")
headers = {"X-Riot-Token": API_KEY}
DB_CONFIG = {
    "dbname": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "host": os.getenv("DB_HOST")
}
REGION = "RU"
API_REGION = "europe"

# Проверка конфигурации
for key, value in DB_CONFIG.items():
    if value is None:
        raise ValueError(f"Переменная окружения для {key} не найдена в .env")

# Подключение к БД
try:
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()
except psycopg2.Error as e:
    raise Exception(f"Ошибка подключения к БД: {e}")

# Маппинг ролей
roles = {'TOP': 1, 'JUNGLE': 2, 'MIDDLE': 3, 'BOTTOM': 4, 'UTILITY': 5}

def check_player_exists(game_name, tag_line):
    cursor.execute("""
        SELECT s.puuid
        FROM players_names p
        LEFT JOIN summoners s USING (game_name, tag_line, region)
        WHERE p.game_name = %s AND p.tag_line = %s AND p.region = %s
    """, (game_name, tag_line, REGION))
    result = cursor.fetchone()
    return result[0] if result else None

def insert_player(game_name, tag_line):
    try:
        # Проверка существования
        puuid = check_player_exists(game_name, tag_line)
        if puuid:
            print(f"Игрок {game_name}#{tag_line} уже в базе")
            return puuid

        # Запрос puuid
        url_account = f"https://{API_REGION}.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{game_name}/{tag_line}"
        r = requests.get(url_account, headers=headers)
        if r.status_code != 200:
            print(f"Ошибка API для {game_name}#{tag_line}: HTTP {r.status_code}, {r.text}")
            return None
        account = r.json()
        if "puuid" not in account:
            print(f"Ошибка для {game_name}#{tag_line}: нет puuid, ответ: {account}")
            return None
        puuid = account["puuid"]

        # Запрос summonerLevel
        url_summoner = f"https://{REGION}.api.riotgames.com/lol/summoner/v4/summoners/by-puuid/{puuid}"
        s = requests.get(url_summoner, headers=headers)
        if s.status_code != 200:
            print(f"Ошибка Summoner API для {puuid}: HTTP {s.status_code}, {s.text}")
            return None
        summoner = s.json()
        if "summonerLevel" not in summoner:
            print(f"Ошибка summoner для {puuid}: нет summonerLevel, ответ: {summoner}")
            return None

        try:
            # players_names
            cursor.execute("""
                INSERT INTO players_names (game_name, tag_line, region)
                VALUES (%s, %s, %s)
                ON CONFLICT ON CONSTRAINT unique_player_name DO NOTHING
                RETURNING player_id
            """, (game_name, tag_line, REGION))
            player_id = cursor.fetchone()
            if player_id:
                player_id = player_id[0]
            else:
                cursor.execute("SELECT player_id FROM players_names WHERE game_name = %s AND tag_line = %s AND region = %s",
                              (game_name, tag_line, REGION))
                player_id = cursor.fetchone()
                if player_id:
                    player_id = player_id[0]
                else:
                    print(f"Не удалось вставить или найти игрока {game_name}#{tag_line} в players_names")
                    return None

            # summoners
            cursor.execute("""
                INSERT INTO summoners (puuid, game_name, tag_line, region, summoner_level)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (puuid) DO NOTHING
            """, (puuid, game_name, tag_line, REGION, summoner["summonerLevel"]))

            conn.commit() 
            print(f"{game_name}#{tag_line} сохранён")
            return puuid
        except psycopg2.Error as e:
            conn.rollback()
            print(f"Ошибка БД для {game_name}#{tag_line}: {e}")
            return None
    except Exception as e:
        print(f"Ошибка для {game_name}#{tag_line}: {e}")
        return None

def insert_match(puuid, match_id):
    try:
        # Проверка, есть ли матч
        cursor.execute("SELECT 1 FROM matches WHERE match_id = %s", (match_id,))
        if cursor.fetchone():
            print(f"Матч {match_id} уже в базе")
            return

        # Получение данных матча
        match_url = f"https://{API_REGION}.api.riotgames.com/lol/match/v5/matches/{match_id}"
        match_resp = requests.get(match_url, headers=headers)
        if match_resp.status_code != 200:
            print(f"Ошибка {match_resp.status_code} при загрузке матча {match_id}: {match_resp.text}")
            return
        match_data = match_resp.json()
        info = match_data["info"]

        if info.get("gameMode") == "ARAM":
            print(f"Матч {match_id} пропущен (режим ARAM)")
            return

        try:
            # matches
            cursor.execute("""
                INSERT INTO matches (match_id, region, game_mode, queue_id, map_id, duration,
                                    start_time, end_time, winner_team)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (match_id) DO NOTHING
            """, (
                match_id, REGION, info.get("gameMode"), info.get("queueId"), info.get("mapId"),
                info.get("gameDuration"),
                datetime.fromtimestamp(info.get("gameStartTimestamp", 0) / 1000),
                datetime.fromtimestamp(info.get("gameEndTimestamp", 0) / 1000),
                100 if info["teams"][0]["win"] else 200
            ))

            # match_players
            for p in info["participants"]:
                participant_puuid = p["puuid"]
                cursor.execute("SELECT 1 FROM summoners WHERE puuid = %s", (participant_puuid,))
                if not cursor.fetchone():
                    if not insert_player(p["riotIdGameName"], p["riotIdTagline"]):
                        print(f"Пропущен игрок {p['riotIdGameName']}#{p['riotIdTagline']} для матча {match_id}")
                        continue

                role = p.get("teamPosition", "UNKNOWN")
                role_id = roles.get(role)
                if not role_id:
                    print(f"Неизвестная роль {role} для {match_id}")
                    continue

                cursor.execute("""
                    INSERT INTO match_players (match_id, puuid, team, champion_id, role_id,
                                              kills, deaths, assists, gold, damage_dealt,
                                              damage_taken, cs, vision_score, win)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT DO NOTHING
                """, (
                    match_id, participant_puuid, 100 if p["teamId"] == 100 else 200,
                    p["championId"], role_id, p["kills"], p["deaths"], p["assists"],
                    p["goldEarned"], p["totalDamageDealtToChampions"], p["totalDamageTaken"],
                    p["totalMinionsKilled"], p["visionScore"], p["win"]
                ))
            cursor.execute("SELECT fill_team_aggregates(%s)", (match_id,))
            cursor.execute("SELECT fill_match_features(%s)", (match_id,))
            conn.commit()
            print(f"Матч {match_id} сохранён")
        except psycopg2.Error as e:
            conn.rollback()
            print(f"Ошибка БД для матча {match_id}: {e}")
    except Exception as e:
        print(f"Ошибка для матча {match_id}: {e}")

def fetch_player_data(game_name, tag_line, max_matches=30):
    puuid = insert_player(game_name, tag_line)
    if not puuid:
        print(f"Не удалось получить puuid для {game_name}#{tag_line}")
        return

    try:
        url = f"https://{API_REGION}.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuid}/ids?count={max_matches}"
        resp = requests.get(url, headers=headers)
        if resp.status_code != 200:
            print(f"Ошибка {resp.status_code} при получении матчей для {game_name}: {resp.text}")
            return

        match_ids = resp.json()
        for match_id in match_ids:
            insert_match(puuid, match_id)
            time.sleep(1.2)
    except Exception as e:
        print(f"Ошибка при получении матчей для {puuid}: {e}")
    finally:
        conn.commit()

game_name = input("Введите game_name: ")
tag_line = input("Введите tag_line: ")
fetch_player_data(game_name, tag_line)

cursor.close()
conn.close()