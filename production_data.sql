INSERT INTO season (name, start_date, end_date, is_current) VALUES ('2024/25', '2024-08-01', '2025-05-31', False);
INSERT INTO season (name, start_date, end_date, is_current) VALUES ('2025/26', '2025-08-01', '2026-05-31', True);
INSERT INTO division (name, season_id) VALUES ('Premier League', (SELECT id FROM season WHERE name = '2024/25'));
INSERT INTO division (name, season_id) VALUES ('Championship', (SELECT id FROM season WHERE name = '2024/25'));
INSERT INTO division (name, season_id) VALUES ('Premier League', (SELECT id FROM season WHERE name = '2025/26'));
INSERT INTO division (name, season_id) VALUES ('Championship', (SELECT id FROM season WHERE name = '2025/26'));
INSERT INTO division (name, season_id) VALUES ('League One', (SELECT id FROM season WHERE name = '2025/26'));
