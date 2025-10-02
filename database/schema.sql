-- Roles table (справочник ролей)
CREATE TABLE roles (
    role_id SERIAL PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE, -- e.g., 'TOP', 'JUNGLE', 'MIDDLE', 'BOTTOM', 'UTILITY'
    CONSTRAINT valid_role CHECK (name IN ('TOP', 'JUNGLE', 'MIDDLE', 'BOTTOM', 'UTILITY'))
);

-- Players_names table (для lookup puuid по имени)
CREATE TABLE players_names (
    player_id SERIAL PRIMARY KEY,
    game_name VARCHAR(100) NOT NULL,
    tag_line VARCHAR(50) NOT NULL,
    region VARCHAR(10) NOT NULL, -- e.g., 'EUW', 'NA'
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT unique_player_name UNIQUE (game_name, tag_line, region)
);
CREATE INDEX idx_player_name ON players_names (game_name, tag_line, region);

-- Summoners table (игроки с puuid)
CREATE TABLE summoners (
    puuid VARCHAR(78) PRIMARY KEY, -- Riot puuid length
    game_name VARCHAR(100) NOT NULL,
    tag_line VARCHAR(50) NOT NULL,
    region VARCHAR(10) NOT NULL, -- e.g., 'EUW', 'NA'
    summoner_level INTEGER NOT NULL,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT unique_summoner_name UNIQUE (game_name, tag_line, region)
);
CREATE INDEX idx_summoner_puuid ON summoners (puuid);
CREATE INDEX idx_summoner_name ON summoners (game_name, tag_line, region);

-- Matches table (метаданные матчей)
CREATE TABLE matches (
    match_id VARCHAR(50) PRIMARY KEY, -- Riot match ID, e.g., 'EUW1_1234567890'
    region VARCHAR(10) NOT NULL, -- e.g., 'EUW', 'NA'
    game_mode VARCHAR(50) NOT NULL, -- e.g., 'CLASSIC'
    queue_id INTEGER NOT NULL, -- e.g., 420 for ranked
    map_id INTEGER NOT NULL, -- e.g., 11 for Summoner's Rift
    duration INTEGER NOT NULL, -- seconds
    start_time TIMESTAMP NOT NULL,
    end_time TIMESTAMP NOT NULL,
    winner_team INTEGER NOT NULL -- 100=blue, 200=red
);
CREATE INDEX idx_match_id ON matches (match_id, region);
CREATE INDEX idx_start_time ON matches (start_time);

-- Match_players table (индивидуальные статы игроков в матче)
CREATE TABLE match_players (
    participant_id SERIAL PRIMARY KEY,
    match_id VARCHAR(50) NOT NULL REFERENCES matches(match_id),
    puuid VARCHAR(78) NOT NULL REFERENCES summoners(puuid),
    team INTEGER NOT NULL, -- 100=blue, 200=red
    champion_id INTEGER NOT NULL, -- References Data Dragon champion ID
    role_id INTEGER NOT NULL REFERENCES roles(role_id),
    kills INTEGER NOT NULL,
    deaths INTEGER NOT NULL,
    assists INTEGER NOT NULL,
    gold INTEGER NOT NULL,
    damage_dealt INTEGER NOT NULL,
    damage_taken INTEGER NOT NULL,
    cs INTEGER NOT NULL, -- creep score
    vision_score INTEGER NOT NULL,
    win BOOLEAN NOT NULL
);
CREATE INDEX idx_match_puuid ON match_players (match_id, puuid);
CREATE INDEX idx_puuid ON match_players (puuid);
CREATE INDEX idx_match_players_role ON match_players (role_id);

-- Team_aggregates table (агрегированные статы команд)
CREATE TABLE team_aggregates (
    agg_id SERIAL PRIMARY KEY,
    match_id VARCHAR(50) NOT NULL REFERENCES matches(match_id),
    team INTEGER NOT NULL, -- 100=blue, 200=red
    kills INTEGER NOT NULL,
    deaths INTEGER NOT NULL,
    assists INTEGER NOT NULL,
    total_cs INTEGER NOT NULL,
    total_vision INTEGER NOT NULL,
    gold INTEGER NOT NULL,
    damage_dealt INTEGER NOT NULL,
    damage_taken INTEGER NOT NULL,
    win BOOLEAN NOT NULL,
    player_count INTEGER NOT NULL, -- e.g., 5
    mean_kda_ind FLOAT NOT NULL -- average KDA per player
);
CREATE INDEX idx_team_match ON team_aggregates (match_id, team);

-- Match_features table (разницы метрик для ML)
CREATE TABLE match_features (
    feature_id SERIAL PRIMARY KEY,
    match_id VARCHAR(50) NOT NULL REFERENCES matches(match_id),
    kills_diff INTEGER NOT NULL, -- blue - red
    deaths_diff INTEGER NOT NULL,
    assists_diff INTEGER NOT NULL,
    gold_diff INTEGER NOT NULL,
    damage_diff INTEGER NOT NULL,
    damage_taken_diff INTEGER NOT NULL,
    cs_diff INTEGER NOT NULL,
    vision_diff INTEGER NOT NULL,
    mean_kda_diff FLOAT NOT NULL,
    win_blue BOOLEAN NOT NULL -- target for ML
);
CREATE INDEX idx_feature_match ON match_features (match_id);