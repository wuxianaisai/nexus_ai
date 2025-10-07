import psycopg2
import numpy as np
import pandas as pd
import joblib
from sklearn.preprocessing import StandardScaler
from decimal import Decimal
from database import insert_player, fetch_player_data
from config import DB_CONFIG, ROLES

# Загрузка модели и scaler
try:
    model = joblib.load("team_lr_model.pkl")
    scaler = joblib.load("scaler.pkl")
except Exception as e:
    raise Exception(f"Ошибка загрузки модели или scaler: {e}")

def get_champion_id(champion_name):
    """Получает champion_id по имени чемпиона"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        cursor.execute("SELECT champion_id FROM champions WHERE champion_name = %s", (champion_name,))
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        if result:
            return result[0]
        print(f"Чемпион {champion_name} не найден в таблице champions")
        return None
    except psycopg2.Error as e:
        print(f"Ошибка БД при получении champion_id для {champion_name}: {e}")
        return None

def get_player_matches(puuid, champion_id, role_id, min_matches=3):
    """
    Ищет матчи игрока по критериям:
    1. Чемпион + роль
    2. Роль (любой чемпион)
    3. Последние матчи
    Возвращает список match_id
    """
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        match_ids = []

        # 1. Матчи с чемпионом и ролью
        if champion_id and role_id:
            cursor.execute("""
                SELECT mp.match_id
                FROM match_players mp
                JOIN matches m ON mp.match_id = m.match_id
                WHERE mp.puuid = %s
                AND mp.champion_id = %s
                AND mp.role_id = %s
                AND m.queue_id IN (420, 440)
                ORDER BY m.start_time DESC
                LIMIT %s
            """, (puuid, champion_id, role_id, min_matches))
            match_ids = [row[0] for row in cursor.fetchall()]

        # 2. Если недостаточно, ищем матчи по роли
        if len(match_ids) < min_matches and role_id:
            remaining = min_matches - len(match_ids)
            cursor.execute("""
                SELECT mp.match_id
                FROM match_players mp
                JOIN matches m ON mp.match_id = m.match_id
                WHERE mp.puuid = %s
                AND mp.role_id = %s
                AND m.queue_id IN (420, 440)
                AND mp.match_id NOT IN %s
                ORDER BY m.start_time DESC
                LIMIT %s
            """, (puuid, role_id, tuple(match_ids) if match_ids else ('',), remaining))
            match_ids.extend([row[0] for row in cursor.fetchall()])

        # 3. Если всё ещё недостаточно, берём последние матчи
        if len(match_ids) < min_matches:
            remaining = min_matches - len(match_ids)
            cursor.execute("""
                SELECT mp.match_id
                FROM match_players mp
                JOIN matches m ON mp.match_id = m.match_id
                WHERE mp.puuid = %s
                AND m.queue_id IN (420, 440)
                AND mp.match_id NOT IN %s
                ORDER BY m.start_time DESC
                LIMIT %s
            """, (puuid, tuple(match_ids) if match_ids else ('',), remaining))
            match_ids.extend([row[0] for row in cursor.fetchall()])

        cursor.close()
        conn.close()
        return match_ids
    except psycopg2.Error as e:
        print(f"Ошибка БД при получении матчей для puuid {puuid}: {e}")
        return []

def get_match_features(match_ids):
    """
    Получает данные из match_features для списка match_id.
    Возвращает усреднённые признаки (10 признаков).
    """
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()

        if not match_ids:
            # Средние значения по базе
            cursor.execute("""
                SELECT AVG(kills_diff), AVG(deaths_diff), AVG(assists_diff),
                       AVG(gold_diff), AVG(damage_diff), AVG(damage_taken_diff),
                       AVG(cs_diff), AVG(vision_diff), AVG(mean_kda_diff), AVG(team_kda_diff)
                FROM match_features
                WHERE match_id IN (SELECT match_id FROM matches WHERE queue_id IN (420, 440))
            """)
            result = cursor.fetchone()
            cursor.close()
            conn.close()
            if result and any(v is not None for v in result):
                return [float(x) if isinstance(x, Decimal) else x for x in result]
            return [0] * 10

        cursor.execute("""
            SELECT kills_diff, deaths_diff, assists_diff,
                   gold_diff, damage_diff, damage_taken_diff,
                   cs_diff, vision_diff, mean_kda_diff, team_kda_diff
            FROM match_features
            WHERE match_id IN %s
        """, (tuple(match_ids),))
        features = cursor.fetchall()
        cursor.close()
        conn.close()
        if not features:
            return get_match_features([]) 
        return [np.mean([float(f[i]) if isinstance(f[i], Decimal) else f[i] for f in features]) for i in range(10)]
    except psycopg2.Error as e:
        print(f"Ошибка БД при получении match_features: {e}")
        return get_match_features([])

def predict_match_outcome(blue_team, red_team):
    """
    Принимает списки игроков (game_name, tag_line, role, champion) для blue и red команд.
    Возвращает вероятность победы blue_team.
    """
    feature_names = ["kills_diff", "deaths_diff", "assists_diff", "gold_diff", "damage_diff", 
                     "damage_taken_diff", "cs_diff", "vision_diff", "mean_kda_diff", "team_kda_diff"]
    blue_features = []
    red_features = []

    for team, team_name in [(blue_team, "blue"), (red_team, "red")]:
        team_features = []
        for i, player in enumerate(team, 1):
            game_name = player['game_name']
            tag_line = player['tag_line']
            role = player['role']
            champion = player['champion']

            # Проверяем/добавляем игрока
            try:
                puuid = insert_player(game_name, tag_line)
                if not puuid:
                    print(f"Не удалось добавить игрока {game_name}#{tag_line}, используются средние значения")
                    team_features.append(get_match_features([]))
                    continue
            except ValueError as e:
                raise ValueError(f"Ошибка для игрока {i} ({game_name}#{tag_line}) в команде {team_name}: {str(e)}")

            # Получение champion_id и role_id
            champion_id = get_champion_id(champion)
            role_id = ROLES.get(role.upper(), 0)

            # Если игрока только что добавили, загружаем его матчи
            try:
                conn = psycopg2.connect(**DB_CONFIG)
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM match_players WHERE puuid = %s", (puuid,))
                if cursor.fetchone()[0] == 0:
                    print(f"Загружаем матчи для {game_name}#{tag_line}")
                    fetch_player_data(game_name, tag_line, max_matches=20)
                cursor.close()
                conn.close()
            except psycopg2.Error as e:
                print(f"Ошибка БД при проверке матчей для {game_name}#{tag_line}: {e}")
                team_features.append(get_match_features([]))
                continue

            # Поиск подходящих матчей
            match_ids = get_player_matches(puuid, champion_id, role_id)
            if not match_ids:
                print(f"Нет подходящих матчей для {game_name}#{tag_line} ({champion}, {role}), используются средние значения")
                team_features.append(get_match_features([]))
            else:
                print(f"Найдено {len(match_ids)} матчей для {game_name}#{tag_line} ({champion}, {role})")
                team_features.append(get_match_features(match_ids))

        # Усреднение признаки по команде
        team_features = [np.mean([float(f[i]) if isinstance(f[i], Decimal) else f[i] for f in team_features]) for i in range(10)]
        if team_name == "blue":
            blue_features = team_features
        else:
            red_features = team_features

    # Вектор признаков
    feature_vector = [blue_features[i] - red_features[i] for i in range(10)]
    feature_vector = pd.DataFrame([feature_vector], columns=feature_names)

    # Нормализация
    try:
        feature_vector_scaled = scaler.transform(feature_vector)
    except Exception as e:
        print(f"Ошибка при нормализации признаков: {e}")
        return 0.5

    # Предсказание
    try:
        prob_blue_win = model.predict_proba(feature_vector_scaled)[0][1]
        return prob_blue_win
    except Exception as e:
        print(f"Ошибка при предсказании: {e}")
        return 0.5  # Fallback на 50% вероятность
    
def main():
    """Основная функция для ввода данных и предсказания"""
    valid_roles = ["TOP", "JUNGLE", "MIDDLE", "BOTTOM", "UTILITY"]
    blue_team = []
    red_team = []

    print("Введите данные для команды Blue (5 игроков):")
    for i in range(5):
        print(f"Игрок {i+1}:")
        game_name = input("  game_name: ")
        tag_line = input("  tag_line: ")
        role = input("  Роль (TOP, JUNGLE, MIDDLE, BOTTOM, UTILITY): ").upper()
        if role not in valid_roles:
            print(f"Неверная роль {role}. Допустимые роли: {', '.join(valid_roles)}. Используется UNKNOWN.")
            role = "UNKNOWN"
        champion = input("  Чемпион: ")
        blue_team.append((game_name, tag_line, role, champion))

    print("\nВведите данные для команды Red (5 игроков):")
    for i in range(5):
        print(f"Игрок {i+1}:")
        game_name = input("  game_name: ")
        tag_line = input("  tag_line: ")
        role = input("  Роль (TOP, JUNGLE, MIDDLE, BOTTOM, UTILITY): ").upper()
        if role not in valid_roles:
            print(f"Неверная роль {role}. Допустимые роли: {', '.join(valid_roles)}. Используется UNKNOWN.")
            role = "UNKNOWN"
        champion = input("  Чемпион: ")
        red_team.append((game_name, tag_line, role, champion))

    # Предсказание
    prob_blue_win = predict_match_outcome(blue_team, red_team)
    print(f"\nВероятность победы Blue: {prob_blue_win*100:.2f}%")
    print(f"Вероятность победы Red: {(1-prob_blue_win)*100:.2f}%")

if __name__ == "__main__":
    main()