\set ON_ERROR_STOP on

DO $$
DECLARE
    n integer;
    ok boolean;
BEGIN
    SELECT count(*) INTO n FROM information_schema.tables
     WHERE table_schema='public' AND table_type='BASE TABLE';
    IF n <> 12 THEN RAISE EXCEPTION 'Expected 12 tables, found %', n; END IF;

    SELECT count(*) INTO n FROM information_schema.table_constraints
     WHERE constraint_schema='public' AND constraint_type='FOREIGN KEY';
    IF n <> 17 THEN RAISE EXCEPTION 'Expected 17 foreign keys, found %', n; END IF;

    IF (SELECT count(*) FROM users) <> 10 OR
       (SELECT count(*) FROM categories) <> 8 OR
       (SELECT count(*) FROM sources) <> 5 OR
       (SELECT count(*) FROM audiences) <> 3 OR
       (SELECT count(*) FROM events) <> 15 OR
       (SELECT count(*) FROM media) <> 25 OR
       (SELECT count(*) FROM announcements) <> 12 OR
       (SELECT count(*) FROM playlists) <> 5 OR
       (SELECT count(*) FROM playlist_items) <> 30 OR
       (SELECT count(*) FROM displays) <> 1 OR
       (SELECT count(*) FROM schedules) <> 5 THEN
        RAISE EXCEPTION 'Seed row counts do not match the project specification';
    END IF;

    IF EXISTS (
        SELECT 1 FROM playlist_items
        WHERE num_nonnulls(media_id,announcement_id,event_id) <> 1
    ) THEN RAISE EXCEPTION 'Playlist item content reference is invalid'; END IF;

    IF EXISTS (
        SELECT 1 FROM playlist_items
        GROUP BY playlist_id, position HAVING count(*) > 1
    ) THEN RAISE EXCEPTION 'Playlist position is duplicated'; END IF;

    SELECT password_hash = crypt('ChangeMe-Admin-2026', password_hash)
      INTO ok FROM users WHERE username='admin';
    IF ok IS DISTINCT FROM true THEN RAISE EXCEPTION 'Admin bcrypt hash verification failed'; END IF;

    ok := false;
    BEGIN
        INSERT INTO playlist_items(playlist_id,position,display_duration)
        VALUES (1,99,10);
    EXCEPTION WHEN check_violation THEN ok := true;
    END;
    IF NOT ok THEN RAISE EXCEPTION 'Missing exactly-one-content CHECK'; END IF;

    ok := false;
    BEGIN
        INSERT INTO playlist_items(playlist_id,position,display_duration,media_id)
        VALUES (1,1,10,1);
    EXCEPTION WHEN unique_violation THEN ok := true;
    END;
    IF NOT ok THEN RAISE EXCEPTION 'Missing unique playlist position constraint'; END IF;

    ok := false;
    BEGIN
        INSERT INTO events(title,event_date,location,status,organizer_id,category_id)
        VALUES ('Invalid FK test',now(),'Test','planned',999999,1);
    EXCEPTION WHEN foreign_key_violation THEN ok := true;
    END;
    IF NOT ok THEN RAISE EXCEPTION 'Missing event organizer foreign key'; END IF;

    RAISE NOTICE 'PASS: 12 tables, 17 foreign keys, and required seed counts';
    RAISE NOTICE 'PASS: bcrypt hash, playlist XOR and position, and event organizer FK';
END $$;

SELECT 'Roles' AS table_name,count(*) FROM roles UNION ALL
SELECT 'Users',count(*) FROM users UNION ALL
SELECT 'Categories',count(*) FROM categories UNION ALL
SELECT 'Sources',count(*) FROM sources UNION ALL
SELECT 'Audiences',count(*) FROM audiences UNION ALL
SELECT 'Events',count(*) FROM events UNION ALL
SELECT 'Media',count(*) FROM media UNION ALL
SELECT 'Announcements',count(*) FROM announcements UNION ALL
SELECT 'Playlists',count(*) FROM playlists UNION ALL
SELECT 'PlaylistItems',count(*) FROM playlist_items UNION ALL
SELECT 'Displays',count(*) FROM displays UNION ALL
SELECT 'Schedules',count(*) FROM schedules
ORDER BY table_name;
