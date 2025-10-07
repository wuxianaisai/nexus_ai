-- Функция для обновления last_updated
CREATE OR REPLACE FUNCTION update_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.last_updated = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Триггер для players_names
CREATE TRIGGER update_players_names_timestamp
BEFORE UPDATE ON players_names
FOR EACH ROW EXECUTE FUNCTION update_timestamp();