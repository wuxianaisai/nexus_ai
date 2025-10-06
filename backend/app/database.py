import requests
import psycopg2
from datetime import datetime
import time
import json
from config import DB_CONFIG, API_KEY, HEADERS, REGION, API_REGION, ROLES

def load_mastery(puuid):
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        url = f"https://{REGION}.api.riotgames.com/lol/champion-mastery/v4/champion-masteries/by-puuid/{puuid}"
        response = requests.get(url, headers=HEADERS)
        time.sleep(1.2)
        if response.status_code != 200:
            print(f"Ошибка загрузки мастерства для puuid {puuid}: HTTP {response.status_code}, {response.text}")
            cursor.close()
            conn.close()
            return

        data = response.json()
        for mastery in data:
            champion_id = mastery["championId"]
            champion_level = mastery["championLevel"]
            champion_points = mastery["championPoints"]
            last_play_time = datetime.fromtimestamp(mastery["lastPlayTime"] / 1000) if mastery.get("lastPlayTime") else None
            tokens_earned = min(mastery.get("tokensEarned", 0), 20)
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
        cursor.close()
        conn.close()
    except psycopg2.Error as e:
        print(f"Ошибка БД при загрузке мастерства для puuid {puuid}: {e}")
        if 'conn' in locals():
            conn.rollback()
            cursor.close()
            conn.close()

def check_player_exists(game_name, tag_line):
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT s.puuid
            FROM players_names p
            LEFT JOIN summoners s USING (game_name, tag_line, region)
            WHERE p.game_name = %s AND p.tag_line = %s AND p.region = %s
        """, (game_name, tag_line, REGION))
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        return result[0] if result else None
    except psycopg2.Error as e:
        print(f"Ошибка БД при проверке игрока {game_name}#{tag_line}: {e}")
        if 'conn' in locals():
            cursor.close()
            conn.close()
        return None

def insert_player(game_name, tag_line):
    try:
        puuid = check_player_exists(game_name, tag_line)
        if puuid:
            print(f"Игрок {game_name}#{tag_line} уже в базе")
            return puuid

        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()

        # Запрос puuid
        url_account = f"https://{API_REGION}.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{game_name}/{tag_line}"
        r = requests.get(url_account, headers=HEADERS)
        time.sleep(1.2)
        if r.status_code != 200:
            print(f"Ошибка API для {game_name}#{tag_line}: HTTP {r.status_code}, {r.text}")
            cursor.close()
            conn.close()
            return None
        account = r.json()
        if "puuid" not in account:
            print(f"Ошибка для {game_name}#{tag_line}: нет puuid, ответ: {account}")
            cursor.close()
            conn.close()
            return None
        puuid = account["puuid"]

        # Запрос summonerLevel
        url_summoner = f"https://{REGION}.api.riotgames.com/lol/summoner/v4/summoners/by-puuid/{puuid}"
        s = requests.get(url_summoner, headers=HEADERS)
        time.sleep(1.2)
        if s.status_code != 200:
            print(f"Ошибка Summoner API для {puuid}: HTTP {s.status_code}, {s.text}")
            cursor.close()
            conn.close()
            return None
        summoner = s.json()
        if "summonerLevel" not in summoner:
            print(f"Ошибка summoner для {puuid}: нет summonerLevel, ответ: {summoner}")
            cursor.close()
            conn.close()
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
                    cursor.close()
                    conn.close()
                    return None

            # summoners
            cursor.execute("""
                INSERT INTO summoners (puuid, game_name, tag_line, region, summoner_level)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (puuid) DO NOTHING
            """, (puuid, game_name, tag_line, REGION, summoner["summonerLevel"]))

            conn.commit()
            print(f"{game_name}#{tag_line} сохранён")

            # Загрузка мастерства
            load_mastery(puuid)
            cursor.close()
            conn.close()
            return puuid
        except psycopg2.Error as e:
            conn.rollback()
            print(f"Ошибка БД для {game_name}#{tag_line}: {e}")
            cursor.close()
            conn.close()
            return None
    except Exception as e:
        print(f"Ошибка для {game_name}#{tag_line}: {e}")
        if 'conn' in locals():
            cursor.close()
            conn.close()
        return None

def insert_match(puuid, match_id):
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()

        # Проверка, есть ли матч
        cursor.execute("SELECT 1 FROM matches WHERE match_id = %s", (match_id,))
        if cursor.fetchone():
            print(f"Матч {match_id} уже в базе")
            cursor.close()
            conn.close()
            return

        # Получение данных матча
        match_url = f"https://{API_REGION}.api.riotgames.com/lol/match/v5/matches/{match_id}"
        match_resp = requests.get(match_url, headers=HEADERS)
        time.sleep(1.2)
        if match_resp.status_code != 200:
            print(f"Ошибка {match_resp.status_code} при загрузке матча {match_id}: {match_resp.text}")
            cursor.close()
            conn.close()
            return
        match_data = match_resp.json()
        info = match_data["info"]

        if info.get("gameMode") == "ARAM":
            print(f"Матч {match_id} пропущен (режим ARAM)")
            cursor.close()
            conn.close()
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
                role_id = ROLES.get(role)
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
            cursor.close()
            conn.close()
        except psycopg2.Error as e:
            conn.rollback()
            print(f"Ошибка БД для матча {match_id}: {e}")
            cursor.close()
            conn.close()
    except Exception as e:
        print(f"Ошибка для матча {match_id}: {e}")
        if 'conn' in locals():
            cursor.close()
            conn.close()

def fetch_player_data(game_name, tag_line, max_matches=30):
    puuid = insert_player(game_name, tag_line)
    if not puuid:
        print(f"Не удалось получить puuid для {game_name}#{tag_line}")
        return

    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        url = f"https://{API_REGION}.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuid}/ids?count={max_matches}"
        resp = requests.get(url, headers=HEADERS)
        time.sleep(1.2)
        if resp.status_code != 200:
            print(f"Ошибка {resp.status_code} при получении матчей для {game_name}: {resp.text}")
            cursor.close()
            conn.close()
            return

        match_ids = resp.json()
        for match_id in match_ids:
            insert_match(puuid, match_id)
            time.sleep(1.2)
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Ошибка при получении матчей для {puuid}: {e}")
        if 'conn' in locals():
            cursor.close()
            conn.close()

if __name__ == "__main__":
    game_name = input("Введите game_name: ")
    tag_line = input("Введите tag_line: ")
    fetch_player_data(game_name, tag_line)