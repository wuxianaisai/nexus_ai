DO $$
DECLARE
    m_id VARCHAR(50);
BEGIN
    FOR m_id IN SELECT match_id FROM matches LOOP
        PERFORM fill_team_aggregates(m_id);
        PERFORM fill_match_features(m_id);
    END LOOP;
END $$;