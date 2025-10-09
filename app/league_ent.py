import psycopg2
from config import DB_CONFIG
from database import load_league_entries
import time

def get_all_summoners():
    """Получает список всех puuid из таблицы summoners."""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        cursor.execute("SELECT puuid FROM summoners")
        summoners = [row[0] for row in cursor.fetchall()]
        cursor.close()
        conn.close()
        return summoners
    except psycopg2.Error as e:
        print(f"Ошибка БД при получении списка summoners: {e}")
        if 'conn' in locals():
            cursor.close()
            conn.close()
        return []

def populate_league_entries():
    """Загружает рейтинг для всех игроков в базе данных."""
    summoners = get_all_summoners()
    total = len(summoners)
    print(f"Найдено {total} игроков для обновления рейтинга.")

    for i, puuid in enumerate(summoners, 1):
        print(f"Обработка игрока {i}/{total} (puuid: {puuid})")
        try:
            load_league_entries(puuid)
            print(f"Рейтинг для puuid {puuid} успешно обновлён")
        except Exception as e:
            print(f"Ошибка при обработке puuid {puuid}: {e}")
        time.sleep(1.2)

if __name__ == "__main__":
    print("Запуск скрипта для заполнения таблицы league_entries...")
    populate_league_entries()
    print("Обработка завершена.")