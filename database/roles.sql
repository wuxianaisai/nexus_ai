INSERT INTO roles (name) VALUES
	('TOP'),
	('JUNGLE'),
	('MIDDLE'),
	('BOTTOM'),
	('UTILITY')
ON CONFLICT (name) DO NOTHING;