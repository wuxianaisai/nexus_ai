-- Функция для заполнения team_aggregates
CREATE OR REPLACE FUNCTION fill_team_aggregates(match_id_text VARCHAR(50)) RETURNS VOID AS $$
BEGIN
    INSERT INTO team_aggregates (match_id, team, kills, deaths, assists, total_cs, total_vision, gold, damage_dealt, damage_taken, win, player_count, mean_kda_ind, team_kda, team_win)
    SELECT
        mp.match_id,
        mp.team,
        SUM(mp.kills) AS kills,
        SUM(mp.deaths) AS deaths,
        SUM(mp.assists) AS assists,
        SUM(mp.cs) AS total_cs,
        SUM(mp.vision_score) AS total_vision,
        SUM(mp.gold) AS gold,
        SUM(mp.damage_dealt) AS damage_dealt,
        SUM(mp.damage_taken) AS damage_taken,
        MAX(mp.win::int)::boolean AS win,
        COUNT(*) AS player_count,
        AVG((mp.kills + mp.assists) / COALESCE(NULLIF(mp.deaths, 0), 1)) AS mean_kda_ind,
        (SUM(mp.kills) + SUM(mp.assists)) / COALESCE(NULLIF(SUM(mp.deaths), 0), 1) AS team_kda,
        MAX(mp.win::int)::boolean AS team_win  -- Assuming team_win is the same as win
    FROM match_players mp
    WHERE mp.match_id = match_id_text
    GROUP BY mp.match_id, mp.team
    ON CONFLICT (agg_id) DO NOTHING;
END;
$$ LANGUAGE plpgsql;

-- Функция для заполнения match_features
CREATE OR REPLACE FUNCTION fill_match_features(match_id_text VARCHAR(50)) RETURNS VOID AS $$
BEGIN
    INSERT INTO match_features (match_id, kills_diff, deaths_diff, assists_diff, gold_diff, damage_diff, damage_taken_diff, cs_diff, vision_diff, mean_kda_diff, team_kda_diff, win_blue)
    SELECT
        blue.match_id,
        blue.kills - red.kills AS kills_diff,
        blue.deaths - red.deaths AS deaths_diff,
        blue.assists - red.assists AS assists_diff,
        blue.gold - red.gold AS gold_diff,
        blue.damage_dealt - red.damage_dealt AS damage_diff,
        blue.damage_taken - red.damage_taken AS damage_taken_diff,
        blue.total_cs - red.total_cs AS cs_diff,
        blue.total_vision - red.total_vision AS vision_diff,
        blue.mean_kda_ind - red.mean_kda_ind AS mean_kda_diff,
        blue.team_kda - red.team_kda AS team_kda_diff,
        blue.win AS win_blue
    FROM team_aggregates blue
    JOIN team_aggregates red ON blue.match_id = red.match_id
    WHERE blue.team = 100 AND red.team = 200 AND blue.match_id = match_id_text
    ON CONFLICT (feature_id) DO NOTHING;
END;
$$ LANGUAGE plpgsql;